#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys


def collect_instances(model_dir: Path):
    for instance_dir in sorted(p for p in model_dir.iterdir() if p.is_dir()):
        instance_id = instance_dir.name
        traj_path = instance_dir / f"{instance_id}-traj.txt"
        answer_path = instance_dir / f"{instance_id}.md"

        if not traj_path.exists() or not answer_path.exists():
            continue

        try:
            trajectory = traj_path.read_text(encoding="utf-8").strip()
            answer = answer_path.read_text(encoding="utf-8").strip()
        except Exception:
            continue

        image_paths = []
        if answer:
            # naive markdown image path extraction
            for line in answer.splitlines():
                if "![" in line and "](" in line and ")" in line:
                    start = line.find("](") + 2
                    end = line.find(")", start)
                    if end > start:
                        rel = line[start:end].strip()
                        candidate = (instance_dir / rel).resolve()
                        if candidate.exists():
                            image_paths.append(str(candidate))

        yield {
            "instance_id": instance_id,
            "trajectory": trajectory,
            "answer": answer,
            "answer_path": str(answer_path),
            "trajectory_path": str(traj_path),
            "answer_images": image_paths,
        }


def load_completed_ids(csv_path: Path):
    if not csv_path.exists():
        return set()
    try:
        import pandas as pd
    except Exception:
        # fallback to naive parsing
        completed = set()
        with csv_path.open("r", encoding="utf-8") as f:
            header = f.readline().strip().split(",")
            if "instance_id" not in header:
                return completed
            idx = header.index("instance_id")
            for line in f:
                parts = line.strip().split(",")
                if len(parts) > idx:
                    completed.add(parts[idx])
        return completed

    df = pd.read_csv(csv_path)
    if "instance_id" not in df.columns:
        return set()
    # Only treat as completed if required scores exist.
    # rubrics_total_score must be present, and gsb_results must be non-empty.
    completed = set()
    for _, row in df.iterrows():
        instance_id = str(row.get("instance_id", "")).strip()
        if not instance_id:
            continue
        rubrics_ok = False
        gsb_ok = False
        if "rubrics_total_score" in df.columns:
            rubrics_ok = pd.notna(row.get("rubrics_total_score"))
        if "gsb_results" in df.columns:
            val = row.get("gsb_results")
            gsb_ok = isinstance(val, str) and val.strip() != ""
        if rubrics_ok and gsb_ok:
            completed.add(instance_id)
    return completed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True, help="agent_results model directory")
    ap.add_argument("--completed_csv", required=True, help="existing model_scores CSV path")
    ap.add_argument("--output", required=True, help="output JSONL for remaining instances")
    args = ap.parse_args()

    model_dir = Path(args.inputs)
    completed_csv = Path(args.completed_csv)
    output_path = Path(args.output)

    completed = load_completed_ids(completed_csv)

    remaining = []
    for record in collect_instances(model_dir):
        if record["instance_id"] in completed:
            continue
        remaining.append(record)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for rec in remaining:
            json.dump(rec, f, ensure_ascii=False)
            f.write("\n")

    print(f"Remaining instances: {len(remaining)}")
    print(f"Wrote: {output_path}")


if __name__ == "__main__":
    main()
