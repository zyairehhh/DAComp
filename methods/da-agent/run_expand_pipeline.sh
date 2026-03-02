#!/usr/bin/env bash
set -euo pipefail

export BAILIAN_API_KEY='sk-bc44390720ff44618c73c5020588aaed'
PY='/Users/zhongyiliu/anaconda3/envs/dacomp/bin/python'

cd /Users/zhongyiliu/Desktop/data_agent/DAComp/methods/da-agent

$PY run.py \
  --model deepseek-v3.2 \
  -s exp20_base_exp_revert \
  -t ../../dacomp-da/tasks/dacomp-da.jsonl \
  --example_index 2,7,10,15,19,27,37,39,45,51,65,95 \
  --use_experience \
  --max_steps 80

$PY get_results.py deepseek-v3.2-exp20_base_exp_revert \
  --output_dir ../../dacomp-da/evaluation_suite/agent_results

cd /Users/zhongyiliu/Desktop/data_agent/DAComp/dacomp-da/evaluation_suite
$PY llm_judge.py \
  --rubrics-model deepseek-v3.2 \
  --gsb-model-text deepseek-v3.2 \
  --gsb-model-vis deepseek-v3.2 \
  --inputs agent_results/deepseek-v3.2-exp20_base_exp_revert \
  --max-workers 1

$PY get_score.py
