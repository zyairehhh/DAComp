#!/usr/bin/env python3
"""
Diagnose mismatches between `rubrics_total_score` in model_scores CSV and
scores embedded in `rubrics_result`.

This script does NOT modify official evaluation logic. It only reports cases
where the recorded score may have been parsed from a nested field (for example
when top-level key is "Total Score" instead of "total_score").
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Optional, Tuple

import pandas as pd

from core.tasks import extract_total_score as official_extract_total_score


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if pd.isna(value):  # type: ignore[arg-type]
            return None
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _strip_json_block(raw: str) -> str:
    text = raw.strip()
    if not text:
        return ""
    if text.startswith("```"):
        parts = text.split("\n", 1)
        body = parts[1] if len(parts) > 1 else ""
        end_split = body.rsplit("```", 1)
        body = end_split[0] if len(end_split) > 1 else body
        return body.strip()
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def _parse_json(raw: str) -> Optional[Any]:
    text = _strip_json_block(raw)
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        cleaned = re.sub(r":\s*\+(\d+(?:\.\d+)?)", r": \1", text)
        cleaned = re.sub(r"\\(?![\"\\/bfnrtu0-9])", r"\\\\", cleaned)
        try:
            return json.loads(cleaned)
        except Exception:
            return None


def _normalize_key(key: str) -> str:
    return re.sub(r"[\s_\-]+", "", key.strip().lower())


TOP_LEVEL_SCORE_KEYS = {
    "totalscore",
    "score",
    "overallscore",
    "总得分",
    "总分",
}


def _extract_score_diagnostic(raw: str) -> Tuple[Optional[float], str]:
    """
    Try to extract the intended total score with stronger priority:
    1) top-level total-score-like keys (including "Total Score")
    2) top-level Overall object score
    3) fallback recursive search for score-like keys
    """
    data = _parse_json(raw)
    if not isinstance(data, dict):
        return None, "json_parse_failed"

    # 1) Prefer top-level score keys.
    for key, value in data.items():
        norm = _normalize_key(str(key))
        if norm in TOP_LEVEL_SCORE_KEYS:
            score = _to_float(value)
            if score is not None:
                return score, f"top_level:{key}"

    # 2) Common pattern: top-level Overall section includes total score.
    overall = data.get("Overall")
    if isinstance(overall, dict):
        for key, value in overall.items():
            norm = _normalize_key(str(key))
            if norm in TOP_LEVEL_SCORE_KEYS:
                score = _to_float(value)
                if score is not None:
                    return score, f"top_level:Overall.{key}"

    # 3) Recursive fallback.
    best: Optional[float] = None
    best_path: str = "not_found"

    def walk(obj: Any, path: str) -> None:
        nonlocal best, best_path
        if isinstance(obj, dict):
            for key, value in obj.items():
                norm = _normalize_key(str(key))
                next_path = f"{path}.{key}" if path else str(key)
                if norm in TOP_LEVEL_SCORE_KEYS:
                    score = _to_float(value)
                    if score is not None:
                        best = score
                        best_path = f"nested:{next_path}"
                walk(value, next_path)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                walk(item, f"{path}[{idx}]")

    walk(data, "")
    return best, best_path


def _is_diff(a: Optional[float], b: Optional[float], eps: float = 1e-9) -> bool:
    if a is None and b is None:
        return False
    if a is None or b is None:
        return True
    return math.fabs(a - b) > eps


def _iter_csvs(target: Path) -> list[Path]:
    if target.is_dir():
        return sorted(
            p for p in target.glob("*.csv") if p.name != "overall_results.csv"
        )
    return [target]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        required=True,
        help="CSV file path or model_scores directory",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional output CSV path for mismatch rows",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=50,
        help="Number of mismatch rows to print",
    )
    args = parser.parse_args()

    target = Path(args.target)
    csv_files = _iter_csvs(target)
    if not csv_files:
        raise SystemExit(f"No CSV found under: {target}")

    rows: list[dict[str, Any]] = []
    for csv_path in csv_files:
        df = pd.read_csv(csv_path)
        if "instance_id" not in df.columns or "rubrics_result" not in df.columns:
            continue
        for _, row in df.iterrows():
            raw = row.get("rubrics_result")
            if not isinstance(raw, str) or not raw.strip():
                continue
            recorded = _to_float(row.get("rubrics_total_score"))
            official = official_extract_total_score(raw)
            diag, diag_src = _extract_score_diagnostic(raw)

            mismatch_recorded_vs_official = _is_diff(recorded, official)
            mismatch_recorded_vs_diag = _is_diff(recorded, diag)
            mismatch_official_vs_diag = _is_diff(official, diag)
            if not (
                mismatch_recorded_vs_official
                or mismatch_recorded_vs_diag
                or mismatch_official_vs_diag
            ):
                continue

            rows.append(
                {
                    "csv_file": csv_path.name,
                    "instance_id": row.get("instance_id"),
                    "rubrics_total_score_csv": recorded,
                    "official_extract_total_score": official,
                    "diagnostic_total_score": diag,
                    "diagnostic_source": diag_src,
                    "mismatch_csv_vs_official": mismatch_recorded_vs_official,
                    "mismatch_csv_vs_diagnostic": mismatch_recorded_vs_diag,
                    "mismatch_official_vs_diagnostic": mismatch_official_vs_diag,
                }
            )

    if not rows:
        print("No score mismatch found.")
        return

    out_df = pd.DataFrame(rows)
    out_df = out_df.sort_values(
        by=["csv_file", "instance_id"], ascending=[True, True]
    ).reset_index(drop=True)

    print(f"Mismatch rows: {len(out_df)}")
    print(out_df.head(args.show).to_string(index=False))

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(out_path, index=False)
        print(f"\nWrote mismatch report: {out_path}")


if __name__ == "__main__":
    main()
