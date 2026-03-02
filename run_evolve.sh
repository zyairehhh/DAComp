#!/usr/bin/env bash
# run_evolve.sh — Shell wrapper for the experience card evolution pipeline.
#
# Usage:
#   bash run_evolve.sh [OPTIONS]
#
# Examples:
#   # Interactive: extract from 10 worst cases, validate on top 5
#   bash run_evolve.sh --mode interactive --n-cases 10 --test-n 5
#
#   # Dry-run: propose cards without writing anything
#   bash run_evolve.sh --mode dry-run --n-cases 5
#
#   # Fully automated overnight run
#   bash run_evolve.sh --mode auto --n-cases 20 --test-n 10 --max-iterations 3
#
#   # Skip agent re-run (write cards only, score manually later)
#   bash run_evolve.sh --mode interactive --n-cases 10 --skip-agent-run

set -euo pipefail

PY="/Users/zhongyiliu/anaconda3/envs/dacomp/bin/python"
export BAILIAN_API_KEY="${BAILIAN_API_KEY:-sk-bc44390720ff44618c73c5020588aaed}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVOLVE_DIR="$SCRIPT_DIR/experience_evolution"

echo "========================================"
echo "Experience Card Evolution Pipeline"
echo "Working dir: $EVOLVE_DIR"
echo "========================================"

cd "$EVOLVE_DIR"

$PY evolve_pipeline.py \
  --python "$PY" \
  "$@"
