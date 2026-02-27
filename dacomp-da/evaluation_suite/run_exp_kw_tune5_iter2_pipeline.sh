#!/usr/bin/env bash
ROOT="/Users/zhongyiliu/Desktop/data_agent/DAComp"
PY="/Users/zhongyiliu/anaconda3/envs/dacomp/bin/python"
RUN_SUFFIX="deepseek-v3.2-exp_kw_tune5_iter2_focus"
OUT_DIR="$ROOT/methods/da-agent/output/$RUN_SUFFIX"
EVAL_DIR="$ROOT/dacomp-da/evaluation_suite"

while true; do
  done_count=$(find "$OUT_DIR" -name final_summary.json 2>/dev/null | wc -l | tr -d ' ')
  echo "[$(date '+%F %T')] final_summary done=$done_count/5"
  if [ "$done_count" -ge 5 ]; then
    break
  fi
  sleep 60
done

cd "$ROOT/methods/da-agent" || exit 1
"$PY" get_results.py "$RUN_SUFFIX" --output_dir ../../dacomp-da/evaluation_suite/agent_results || exit 1

cd "$EVAL_DIR" || exit 1
export BAILIAN_API_KEY='sk-bc44390720ff44618c73c5020588aaed'
"$PY" llm_judge.py --rubrics-model deepseek-v3.2 --gsb-model-text deepseek-v3.2 --gsb-model-vis deepseek-v3.2 --inputs "agent_results/$RUN_SUFFIX" --max-workers 1 || exit 1
"$PY" get_score.py || exit 1

"$PY" - <<'PY'
import csv
from pathlib import Path
from statistics import mean
root=Path('/Users/zhongyiliu/Desktop/data_agent/DAComp/dacomp-da/evaluation_suite/model_scores')
base=root/'deepseek-v3.2-baseline__rubrics-deepseek-v3-2__textgsb-deepseek-v3-2__visgsb-deepseek-v3-2.csv'
exp=root/'deepseek-v3.2-exp_kw_tune5_iter2_focus__rubrics-deepseek-v3-2__textgsb-deepseek-v3-2__visgsb-deepseek-v3-2.csv'
out=root/'exp_kw_tune5_iter2_vs_baseline.csv'

def load(p):
    with open(p,newline='',encoding='utf-8') as f:
        return {r['instance_id']:r for r in csv.DictReader(f)}
def f(v):
    try:return float(v)
    except:return None
b=load(base); e=load(exp)
rows=[]
for iid in sorted(set(b)&set(e)):
    bw=f(b[iid].get('weighted_total_score')); ew=f(e[iid].get('weighted_total_score'))
    br=f(b[iid].get('rubrics_total_score')); er=f(e[iid].get('rubrics_total_score'))
    ba=f(b[iid].get('rubric_accuracy_score_pct')); ea=f(e[iid].get('rubric_accuracy_score_pct'))
    rows.append({'instance_id':iid,'delta_weighted':(ew-bw) if bw is not None and ew is not None else None,'delta_rubrics':(er-br) if br is not None and er is not None else None,'delta_accuracy_pct':(ea-ba) if ba is not None and ea is not None else None})
with open(out,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)
wd=[r['delta_weighted'] for r in rows if r['delta_weighted'] is not None]
rd=[r['delta_rubrics'] for r in rows if r['delta_rubrics'] is not None]
ad=[r['delta_accuracy_pct'] for r in rows if r['delta_accuracy_pct'] is not None]
summary=root/'exp_kw_tune5_iter2_summary.txt'
summary.write_text(
    f"cases={len(rows)}\n"
    f"avg_delta_weighted={mean(wd) if wd else 'NA'}\n"
    f"avg_delta_rubrics={mean(rd) if rd else 'NA'}\n"
    f"avg_delta_accuracy_pct={mean(ad) if ad else 'NA'}\n"
    f"improved_weighted={sum(1 for x in wd if x>0)} worse_weighted={sum(1 for x in wd if x<0)}\n",
    encoding='utf-8'
)
print(summary.read_text())
PY

echo "[$(date '+%F %T')] pipeline completed"
