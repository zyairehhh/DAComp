"""Classify why a case failed before extracting patterns.

Avoids wasting LLM tokens on cases that fail due to data limitations or task
ambiguity — patterns from those cases rarely generalise to other tasks.

Failure types:
  knowledge_gap    — agent lacked a reusable analytical principle (fixable by experience)
  execution_error  — code bug / tool crash / syntax error dominated
  data_limitation  — data genuinely insufficient for the task requirement
  ambiguous_task   — task instruction unclear or contradictory

Usage:
  from classify_failures import classify_failure_type, load_failure_type, save_failure_type
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import requests


FailureType = Literal["knowledge_gap", "execution_error", "data_limitation", "ambiguous_task"]

_DEEPSEEK_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
_DEFAULT_MODEL = "deepseek-v3.2"
_CACHE_FILENAME = "{iid}_failure_type.json"


# ---------------------------------------------------------------------------
# LLM call (same pattern as extract_patterns.py)
# ---------------------------------------------------------------------------

def _call_llm(prompt: str, model: str = _DEFAULT_MODEL, max_retries: int = 3) -> str:
    api_key = os.environ.get("BAILIAN_API_KEY", "")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.0,
    }
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(_DEEPSEEK_URL, headers=headers, json=payload, timeout=120)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            print(
                f"[classify_llm] HTTP {resp.status_code} attempt {attempt}: {resp.text[:200]}",
                file=sys.stderr,
            )
        except requests.RequestException as exc:
            print(f"[classify_llm] Error attempt {attempt}: {exc}", file=sys.stderr)
        if attempt < max_retries:
            time.sleep(5 * attempt)
    raise RuntimeError(f"LLM classification failed after {max_retries} attempts")


# ---------------------------------------------------------------------------
# Classification prompt
# ---------------------------------------------------------------------------

_CLASSIFY_PROMPT = """\
You are a data analysis failure analyst. Classify why this data analysis agent failed.

## Task Instruction (first 2000 chars)
{instruction}

## Key Rubric Failures
Rubrics score: {score_pct:.1f}%
Failures:
{failure_summary}

## Agent Trajectory Excerpt (last 3000 chars)
{traj_excerpt}

## Classification Options
Choose EXACTLY ONE:
- knowledge_gap: The agent had the data but applied wrong analytical steps, missed a dimension,
  or used incorrect methodology. A reusable experience card could fix this.
- execution_error: The agent's code/tool crashed, had syntax errors, or produced no output
  due to runtime failures — not a conceptual mistake.
- data_limitation: The required information genuinely does not exist in the provided data,
  making the task unsolvable regardless of methodology.
- ambiguous_task: The task instruction is contradictory, too vague, or requires external
  knowledge not available to the agent.

## Output
Return ONLY a JSON object (no markdown, no explanation):
{{"failure_type": "<one of the four options above>", "reason": "<one sentence justification>"}}
"""


def classify_failure_type(
    instance_id: str,
    instruction: str,
    traj_text: str,
    rubrics_row: Dict[str, Any],
    model: str = _DEFAULT_MODEL,
) -> FailureType:
    """Classify the root cause of failure for a case.

    Falls back to 'knowledge_gap' on any parse error (safe default — we'd
    rather extract unnecessary patterns than miss fixable ones).
    """
    score_pct_raw = rubrics_row.get("rubrics_percentage", "0")
    try:
        score_pct = float(score_pct_raw) if score_pct_raw else 0.0
    except (ValueError, TypeError):
        score_pct = 0.0

    # Build failure summary from rubrics_result
    rr_raw = rubrics_row.get("rubrics_result", "")
    failure_summary = _extract_failure_summary(rr_raw)

    # Use last 3000 chars of trajectory as excerpt
    traj_excerpt = traj_text[-3000:] if len(traj_text) > 3000 else traj_text

    prompt = _CLASSIFY_PROMPT.format(
        instruction=instruction[:2000],
        score_pct=score_pct,
        failure_summary=failure_summary[:2000],
        traj_excerpt=traj_excerpt,
    )

    try:
        raw = _call_llm(prompt, model=model)
        # Find JSON in response
        import re
        match = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
        if not match:
            print(f"[{instance_id}] classify: no JSON in response, defaulting to knowledge_gap",
                  file=sys.stderr)
            return "knowledge_gap"
        result = json.loads(match.group())
        ft = result.get("failure_type", "knowledge_gap")
        valid = {"knowledge_gap", "execution_error", "data_limitation", "ambiguous_task"}
        if ft not in valid:
            return "knowledge_gap"
        reason = result.get("reason", "")
        print(f"[{instance_id}] failure_type={ft}: {reason}", file=sys.stderr)
        return ft  # type: ignore[return-value]
    except Exception as exc:
        print(f"[{instance_id}] classify error: {exc}, defaulting to knowledge_gap",
              file=sys.stderr)
        return "knowledge_gap"


def _extract_failure_summary(rubrics_result_raw: str, max_chars: int = 2000) -> str:
    """Quick summary of failure criteria from rubrics_result JSON string."""
    if not rubrics_result_raw:
        return "(no rubrics data)"
    text = rubrics_result_raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        inner = lines[1:]
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner)
    try:
        obj = json.loads(text)
    except Exception:
        return text[:max_chars]

    lines = []
    _collect_failures(obj, "", lines)
    return "\n".join(lines)[:max_chars] if lines else text[:max_chars]


def _collect_failures(obj: Any, path: str, out: list) -> None:
    if isinstance(obj, dict):
        score = obj.get("score")
        analysis = obj.get("analysis", "")
        if isinstance(score, (int, float)) and float(score) <= 0.5 and analysis:
            out.append(f"[{path}] score={score}: {analysis}")
        for k, v in obj.items():
            if k not in ("score", "analysis", "criterion_type"):
                _collect_failures(v, f"{path}/{k}" if path else k, out)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _collect_failures(item, f"{path}[{i}]", out)


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------

def load_failure_type(patterns_dir: Path, instance_id: str) -> Optional[FailureType]:
    """Load cached failure type from patterns_dir/{iid}_failure_type.json."""
    path = patterns_dir / f"{instance_id}_failure_type.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ft = data.get("failure_type")
        valid = {"knowledge_gap", "execution_error", "data_limitation", "ambiguous_task"}
        return ft if ft in valid else None  # type: ignore[return-value]
    except Exception:
        return None


def save_failure_type(patterns_dir: Path, instance_id: str, failure_type: FailureType) -> None:
    """Persist failure type to patterns_dir/{iid}_failure_type.json."""
    path = patterns_dir / f"{instance_id}_failure_type.json"
    path.write_text(
        json.dumps({"instance_id": instance_id, "failure_type": failure_type}, indent=2),
        encoding="utf-8",
    )
