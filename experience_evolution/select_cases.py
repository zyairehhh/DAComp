"""Select the worst-performing cases from the baseline CSV.

Default sort key: weighted_total_score (rubrics + GSB combined).

Usage:
    python select_cases.py --baseline-csv <path> --n 10
    python select_cases.py --baseline-csv <path> --n 10 --out-file selected_cases.txt
    python select_cases.py --case-file existing_list.txt   # use a pre-existing list
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import List, Optional, Set

# Default column to rank by (lowest = worst).
# weighted_total_score combines rubrics + GSB in the benchmark's own weighting.
DEFAULT_SORT_COLUMN = "weighted_total_score"


def _parse_score(row: dict, column: str) -> float:
    raw = (row.get(column) or "").strip()
    try:
        return float(raw)
    except (ValueError, TypeError):
        return 0.0


def select_worst_cases(
    baseline_csv: Path,
    n: int = 10,
    exclude_ids: Optional[Set[str]] = None,
    sort_by: str = DEFAULT_SORT_COLUMN,
) -> List[str]:
    """Return the n lowest-scoring instance_ids by sort_by column (default: weighted_total_score)."""
    exclude_ids = exclude_ids or set()
    rows: List[tuple[float, str]] = []
    with baseline_csv.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            instance_id = (row.get("instance_id") or "").strip()
            if not instance_id or instance_id in exclude_ids:
                continue
            score = _parse_score(row, sort_by)
            rows.append((score, instance_id))

    rows.sort(key=lambda x: x[0])
    return [iid for _, iid in rows[:n]]


def load_case_file(path: Path) -> List[str]:
    """Load a newline-separated list of instance_ids from a file."""
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Select worst-performing cases from baseline CSV"
    )
    parser.add_argument("--baseline-csv", default=None, help="Path to baseline scores CSV")
    parser.add_argument("--n", type=int, default=10, help="Number of cases to select")
    parser.add_argument(
        "--sort-by",
        default=DEFAULT_SORT_COLUMN,
        help=f"CSV column to rank by ascending (default: {DEFAULT_SORT_COLUMN})",
    )
    parser.add_argument("--out-file", default=None, help="Write selected IDs to this file")
    parser.add_argument(
        "--case-file",
        default=None,
        help="Use a pre-existing list of instance_ids instead of selecting from CSV",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Instance IDs to exclude from selection",
    )
    args = parser.parse_args()

    if args.case_file:
        cases = load_case_file(Path(args.case_file))
    else:
        if not args.baseline_csv:
            parser.error("--baseline-csv is required when --case-file is not provided")
        cases = select_worst_cases(
            Path(args.baseline_csv),
            n=args.n,
            exclude_ids=set(args.exclude),
            sort_by=args.sort_by,
        )

    output = "\n".join(cases)
    if args.out_file:
        Path(args.out_file).write_text(output + "\n", encoding="utf-8")
        print(f"Wrote {len(cases)} case IDs to {args.out_file}", file=sys.stderr)
    print(output)


if __name__ == "__main__":
    main()
