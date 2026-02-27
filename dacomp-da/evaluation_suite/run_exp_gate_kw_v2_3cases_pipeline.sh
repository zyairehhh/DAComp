#!/usr/bin/env bash
set -u
ROOT="/Users/zhongyiliu/Desktop/data_agent/DAComp"
PY="/Users/zhongyiliu/anaconda3/envs/dacomp/bin/python"
RUN_SUFFIX="deepseek-v3.2-exp_gate_kw_v2_3cases_quick"
OUT_DIR="$ROOT/methods/da-agent/output/$RUN_SUFFIX"
EVAL_DIR="$ROOT/dacomp-da/evaluation_suite"

while true; do
  c=$(find "$OUT_DIR" -name final_summary.json 2>/dev/null | wc -l | tr -d ' ' || true)
  echo "[$(date '+%F %T')] final_summary done=$c/3"
  if [ "$c" -ge 3 ]; then
    break
  fi
  sleep 30
done

cd "$ROOT/methods/da-agent"
"$PY" get_results.py "$RUN_SUFFIX" --output_dir ../../dacomp-da/evaluation_suite/agent_results

cd "$EVAL_DIR"
export BAILIAN_API_KEY='sk-bc44390720ff44618c73c5020588aaed'
"$PY" llm_judge.py --rubrics-model deepseek-v3.2 --gsb-model-text deepseek-v3.2 --gsb-model-vis deepseek-v3.2 --inputs "agent_results/$RUN_SUFFIX" --max-workers 1
"$PY" get_score.py

"$PY" compare_model_scores_subset.py \
  --baseline "$EVAL_DIR/model_scores/deepseek-v3.2-baseline__rubrics-deepseek-v3-2__textgsb-deepseek-v3-2__visgsb-deepseek-v3-2.csv" \
  --candidate "$EVAL_DIR/model_scores/deepseek-v3.2-exp_gate_kw_v2_3cases_quick__rubrics-deepseek-v3-2__textgsb-deepseek-v3-2__visgsb-deepseek-v3-2.csv" \
  --out "$EVAL_DIR/model_scores/exp_gate_kw_v2_3cases_vs_baseline.csv"

echo "[$(date '+%F %T')] pipeline completed"
