"""Extract reusable failure patterns from baseline trajectories + rubric evaluations.

For each case, calls an LLM to analyze:
  - The task instruction
  - A truncated version of the agent trajectory (first + last steps)
  - The rubric judge evaluation (what was wrong and why)

And produces a JSON file of candidate experience card patterns.

Usage:
    python extract_patterns.py \\
        --case-ids dacomp-003 dacomp-012 dacomp-021 \\
        --baseline-csv ../../model_scores/deepseek-v3.2-baseline__...csv \\
        --task-file ../../../../dacomp-da/tasks/dacomp-da.jsonl \\
        --traj-dir ../../baseline_agent_results/deepseek-v3.2-baseline \\
        --cards-dir ../../../../dacomp-da/experience_cards \\
        --out-dir patterns/
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from card_utils import load_index, parse_rubrics_percentage, summarize_existing_cards


# ---------------------------------------------------------------------------
# LLM client (standalone, no dependency on evaluation_suite.core)
# ---------------------------------------------------------------------------

_DEEPSEEK_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
_DEFAULT_MODEL = "deepseek-v3.2"


def _call_llm(prompt: str, model: str = _DEFAULT_MODEL, max_retries: int = 5) -> str:
    api_key = os.environ.get("BAILIAN_API_KEY", "")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8192,
        "temperature": 0.0,
    }
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(_DEEPSEEK_URL, headers=headers, json=payload, timeout=300)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            print(
                f"[LLM] HTTP {resp.status_code} on attempt {attempt}: {resp.text[:200]}",
                file=sys.stderr,
            )
        except requests.RequestException as exc:
            print(f"[LLM] Request error on attempt {attempt}: {exc}", file=sys.stderr)
        if attempt < max_retries:
            time.sleep(5 * attempt)
    raise RuntimeError(f"LLM call failed after {max_retries} attempts")


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def load_task_instructions(task_file: Path) -> Dict[str, str]:
    """Load {instance_id: instruction} from JSONL."""
    instructions: Dict[str, str] = {}
    with task_file.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            instructions[record["instance_id"]] = record.get("instruction", "")
    return instructions


def load_rubrics_scores(baseline_csv: Path) -> Dict[str, Dict[str, Any]]:
    """Load rubric data keyed by instance_id from the baseline CSV."""
    scores: Dict[str, Dict[str, Any]] = {}
    with baseline_csv.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            iid = (row.get("instance_id") or "").strip()
            if iid:
                scores[iid] = dict(row)
    return scores


def _parse_rubrics_result(raw: str) -> Optional[Dict]:
    """Parse rubrics_result JSON string from CSV field (strips markdown code fences if present)."""
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    # Strip markdown code fences: ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        inner_lines = lines[1:]
        if inner_lines and inner_lines[-1].strip() == "```":
            inner_lines = inner_lines[:-1]
        text = "\n".join(inner_lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _extract_failure_analyses(rubrics_result: Optional[Dict], max_chars: int = 12000) -> str:
    """Extract the most informative failure analyses from rubrics_result JSON.

    Prioritises criteria with score <= 0.5 (absolute) or where analysis
    text signals incompleteness/error.
    """
    if not rubrics_result:
        return "(rubric evaluation not available)"

    failure_keywords = {
        "did not", "missing", "failed", "no ", "absent", "incomplete",
        "incorrect", "wrong", "error", "not provided", "not shown",
        "partial credit", "0 points", "0.0", "score: 0",
    }

    def _collect(obj: Any, path: str, results: List[tuple[float, str, str]]) -> None:
        if isinstance(obj, dict):
            score = obj.get("score")
            analysis = obj.get("analysis", "")
            if isinstance(score, (int, float)) and isinstance(analysis, str) and analysis:
                is_failure = (
                    float(score) <= 0.5
                    or any(kw in analysis.lower() for kw in failure_keywords)
                )
                if is_failure:
                    results.append((float(score), path, analysis))
            for key, val in obj.items():
                if key not in ("score", "analysis", "criterion_type"):
                    _collect(val, f"{path}/{key}", results)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _collect(item, f"{path}[{i}]", results)

    collected: List[tuple[float, str, str]] = []
    _collect(rubrics_result, "root", collected)
    # Sort by score ascending (worst first)
    collected.sort(key=lambda x: x[0])

    lines: List[str] = []
    total_chars = 0
    for score, path, analysis in collected:
        entry = f"[{path}] score={score}: {analysis}\n"
        if total_chars + len(entry) > max_chars:
            break
        lines.append(entry)
        total_chars += len(entry)

    if not lines:
        # Fallback: dump full JSON truncated
        full = json.dumps(rubrics_result, ensure_ascii=False)
        return full[:max_chars]
    return "".join(lines)


def _truncate_trajectory(traj_text: str, first_n: int = 12, last_n: int = 25) -> str:
    """Return a truncated trajectory keeping first_n + last_n steps."""
    step_pattern = re.compile(r"^--- Step \d+ ---", re.MULTILINE)
    boundaries = [m.start() for m in step_pattern.finditer(traj_text)]
    if not boundaries:
        # No step markers — just truncate raw text
        half = 10000
        if len(traj_text) <= 2 * half:
            return traj_text
        return traj_text[:half] + "\n...[truncated]...\n" + traj_text[-half:]

    total = len(boundaries)
    if total <= first_n + last_n:
        return traj_text

    first_end = boundaries[first_n] if first_n < total else len(traj_text)
    last_start = boundaries[total - last_n] if last_n < total else 0

    first_part = traj_text[:first_end].strip()
    last_part = traj_text[last_start:].strip()
    omitted = total - first_n - last_n
    return f"{first_part}\n\n... [{omitted} steps omitted] ...\n\n{last_part}"


# ---------------------------------------------------------------------------
# Pattern extraction prompt
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """\
You are a data analysis coach. Your job is to identify REUSABLE principles from data analysis failures so that future agents avoid the same mistakes.

## Task Instruction
{instruction}

## Agent Trajectory (truncated — key exploration and reporting steps)
```
{trajectory}
```

## Rubric Evaluation — Failures Found by the Judge
The agent scored {score_pct:.1f}% on the rubrics.
The following specific failures were identified:

{failure_analyses}

## Existing Experience Cards (DO NOT duplicate these)
{existing_cards_summary}

## Your Task
Looking at where the agent scored poorly above, identify up to 3 GENERAL principles that would help a data analysis agent avoid these mistakes in DIFFERENT tasks.

Requirements for each principle:
1. **General** — applies to many data analysis tasks, not specific to this dataset or domain
2. **Actionable** — specific steps or a checklist the agent can follow
3. **Non-trivial** — not obvious ("check your math") or already in the existing cards above
4. **Retrievable** — include keywords that naturally appear in task descriptions requiring this card

## Output Format
Return ONLY a JSON array (no markdown fences, no other text):
[
  {{
    "title": "Short action-oriented title (5-8 words)",
    "when_to_use": "One sentence: what feature in the task triggers this card",
    "experience": "Markdown bullets: 3-6 specific steps the agent should follow",
    "checklist": ["item1", "item2", "item3"],
    "common_failure_prevented": "One sentence: the specific mistake this prevents",
    "keywords": ["word1", "word2"],
    "tags": ["tag1", "tag2", "tag3"],
    "source_criterion": "Rubric path where the failure was observed (e.g. Requirement 1/Criterion 1.2)"
  }}
]

If no general reusable principle can be extracted from this case, return an empty array: []
"""


def extract_patterns_for_case(
    instance_id: str,
    instruction: str,
    traj_path: Path,
    rubrics_row: Dict[str, Any],
    existing_cards_summary: str,
) -> List[Dict]:
    """Extract candidate patterns for one case. Returns list of pattern dicts."""
    # Load trajectory
    traj_text = ""
    if traj_path.exists():
        traj_text = traj_path.read_text(encoding="utf-8", errors="replace")
    truncated_traj = _truncate_trajectory(traj_text)

    # Parse rubrics result
    rubrics_result = _parse_rubrics_result(rubrics_row.get("rubrics_result", ""))
    failure_analyses = _extract_failure_analyses(rubrics_result)
    score_pct = parse_rubrics_percentage(rubrics_row)

    prompt = _EXTRACTION_PROMPT.format(
        instruction=instruction[:3000],
        trajectory=truncated_traj[:20000],
        score_pct=score_pct,
        failure_analyses=failure_analyses[:12000],
        existing_cards_summary=existing_cards_summary,
    )

    print(f"[{instance_id}] Calling LLM for pattern extraction (score={score_pct:.1f}%)…",
          file=sys.stderr)
    raw_response = _call_llm(prompt)

    # Extract JSON from response
    json_match = re.search(r"\[.*\]", raw_response, re.DOTALL)
    if not json_match:
        print(f"[{instance_id}] WARNING: LLM returned no JSON array", file=sys.stderr)
        return []

    try:
        patterns = json.loads(json_match.group())
        if not isinstance(patterns, list):
            return []
        # Annotate with source
        return [{**p, "source_case": instance_id} for p in patterns if isinstance(p, dict)]
    except json.JSONDecodeError as exc:
        print(f"[{instance_id}] WARNING: JSON parse error: {exc}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract failure patterns for selected cases"
    )
    parser.add_argument(
        "--case-ids",
        nargs="+",
        required=True,
        help="Instance IDs to process (e.g. dacomp-003 dacomp-012)",
    )
    parser.add_argument(
        "--baseline-csv",
        required=True,
        help="Path to baseline rubric scores CSV",
    )
    parser.add_argument(
        "--task-file",
        default="../../../../dacomp-da/tasks/dacomp-da.jsonl",
        help="Path to task JSONL file",
    )
    parser.add_argument(
        "--traj-dir",
        default="../../baseline_agent_results/deepseek-v3.2-baseline",
        help="Directory containing per-instance trajectory subdirs",
    )
    parser.add_argument(
        "--cards-dir",
        default="../../../../dacomp-da/experience_cards",
        help="Experience cards directory (contains index.json)",
    )
    parser.add_argument(
        "--out-dir",
        default="patterns",
        help="Output directory for pattern JSON files",
    )
    parser.add_argument(
        "--model",
        default=_DEFAULT_MODEL,
        help="LLM model name to use",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cards_dir = Path(args.cards_dir)

    # Load shared data
    instructions = load_task_instructions(Path(args.task_file))
    scores_by_id = load_rubrics_scores(Path(args.baseline_csv))
    index = load_index(cards_dir)
    existing_summary = summarize_existing_cards(index)

    traj_dir = Path(args.traj_dir)
    total_patterns = 0

    for instance_id in args.case_ids:
        out_path = out_dir / f"{instance_id}_patterns.json"
        if out_path.exists():
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            print(
                f"[{instance_id}] Already extracted {len(existing)} patterns — skipping",
                file=sys.stderr,
            )
            total_patterns += len(existing)
            continue

        instruction = instructions.get(instance_id, "")
        if not instruction:
            print(f"[{instance_id}] WARNING: no instruction found", file=sys.stderr)
            continue

        rubrics_row = scores_by_id.get(instance_id, {})
        if not rubrics_row:
            print(f"[{instance_id}] WARNING: no rubrics row found in CSV", file=sys.stderr)
            continue

        # Find trajectory file
        traj_path = traj_dir / instance_id / f"{instance_id}-traj.txt"

        patterns = extract_patterns_for_case(
            instance_id=instance_id,
            instruction=instruction,
            traj_path=traj_path,
            rubrics_row=rubrics_row,
            existing_cards_summary=existing_summary,
        )

        out_path.write_text(json.dumps(patterns, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[{instance_id}] Extracted {len(patterns)} patterns → {out_path}", file=sys.stderr)
        total_patterns += len(patterns)

    print(f"\nTotal candidate patterns: {total_patterns}", file=sys.stderr)


if __name__ == "__main__":
    main()
