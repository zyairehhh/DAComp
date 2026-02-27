#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/zhongyiliu/Desktop/data_agent/DAComp"
PY="/Users/zhongyiliu/anaconda3/envs/dacomp/bin/python"
RUN_SUFFIX="deepseek-v3.2-exp_kw_tune10_base_exp"
AGENT_OUT="$ROOT/methods/da-agent/output/$RUN_SUFFIX"
EVAL_DIR="$ROOT/dacomp-da/evaluation_suite"

# wait until 10 final summaries are generated or agent run process exits
while true; do
  done_count=$(find "$AGENT_OUT" -name final_summary.json 2>/dev/null | wc -l | tr -d ' ')
  running=$(ps -ef | grep "run.py --model deepseek-v3.2 -s exp_kw_tune10_base_exp" | grep -v grep | wc -l | tr -d ' ')
  echo "[$(date '+%F %T')] done_count=$done_count running=$running"
  if [[ "$done_count" -ge 10 ]]; then
    break
  fi
  if [[ "$running" -eq 0 ]]; then
    # stop waiting if run process ended unexpectedly
    break
  fi
  sleep 30
done

cd "$ROOT/methods/da-agent"
$PY get_results.py "$RUN_SUFFIX" --output_dir ../../dacomp-da/evaluation_suite/agent_results

cd "$EVAL_DIR"
export BAILIAN_API_KEY='sk-bc44390720ff44618c73c5020588aaed'
$PY llm_judge.py \
  --rubrics-model deepseek-v3.2 \
  --gsb-model-text deepseek-v3.2 \
  --gsb-model-vis deepseek-v3.2 \
  --inputs "agent_results/$RUN_SUFFIX" \
  --max-workers 1

$PY get_score.py
