import json
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path("/Users/zhongyiliu/Desktop/data_agent/DAComp")
TASKS_PATH = ROOT / "dacomp-da" / "tasks" / "dacomp-da.jsonl"
EXPERIENCE_PATH = ROOT / "methods" / "da-agent" / "da_agent" / "agent" / "experience.py"
EXPERIENCE_DIR = ROOT / "dacomp-da" / "experience_cards"


EXPECTED = {
    # Cases that should retrieve NO experience cards (simple / non-matching tasks)
    "dacomp-002": {"has_snippet": False},
    "dacomp-004": {"has_snippet": False},
    "dacomp-006": {"has_snippet": False},
    "dacomp-012": {"has_snippet": False},
    "dacomp-038": {"has_snippet": False},
    # Cases that should retrieve specific cards (positive anchors)
    "dacomp-058": {"has_snippet": True, "must_contain": ["[exp-da-009]"]},
    "dacomp-034": {"has_snippet": True, "must_contain": ["[exp-da-005]"]},
}


def load_tasks():
    tasks = {}
    with TASKS_PATH.open() as f:
        for line in f:
            obj = json.loads(line)
            tasks[obj["instance_id"]] = obj["instruction"]
    return tasks


def main():
    experience = SourceFileLoader("experience", str(EXPERIENCE_PATH)).load_module()
    tasks = load_tasks()

    failed = False
    for instance_id, expectation in EXPECTED.items():
        instruction = tasks[instance_id]
        snippet = experience.build_experience_snippet(
            instruction,
            experience_dir=str(EXPERIENCE_DIR),
        )
        has_snippet = bool(snippet.strip())
        print(f"{instance_id}: has_snippet={has_snippet}")

        if has_snippet != expectation["has_snippet"]:
            print(
                f"  FAIL: expected has_snippet={expectation['has_snippet']}, got {has_snippet}"
            )
            failed = True
            continue

        for token in expectation.get("must_contain", []):
            if token not in snippet:
                print(f"  FAIL: expected token `{token}` not found")
                failed = True
        if has_snippet:
            preview = snippet.replace("\n", " | ")
            print(f"  snippet={preview[:240]}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
