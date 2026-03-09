# exp_v5 Resume Notes

Last updated: 2026-03-06 20:30

---

## 当前状态（中断时）

### iter1（中断）

| 步骤 | 状态 | 说明 |
|------|------|------|
| 模式提取（15 cases） | ✅ 完成 | `iter1/patterns/` 已有缓存，重启跳过 |
| 合成新卡 | ✅ 完成 | `iter1/synthesis_cache.json`，7 张卡，重启跳过 |
| Regression guard | ✅ 完成 | `iter1/guard_cache.json` 已缓存 |
| 写卡（exp-da-001~007） | ⚠️ 需修复 | `cards_written.json` 存在但 `cards/index.json` 为空（被 iter2 prune 清空） |
| Agent r0（10 cases） | ✅ 完成 | `output/deepseek-v3.2-evolve_exp_v5_iter1_r0/`（10/10 case）|
| Agent r1（10 cases） | ⚠️ 部分 | `output/deepseek-v3.2-evolve_exp_v5_iter1_r1/`（8/10 case） |
| Agent r2 | ❌ 未开始 | 无输出目录 |
| Judge × 3 | ❌ 未完成 | — |
| 评分比较 | ✅ iter1 完成 | iter1 已跑完评分（否则不会进入 iter2），结果见 evolution_log.json |
| iter1 complete 标记 | ❌ 缺失 | iter_complete.json 未生成（被 kill 前未来得及写）|

### iter2（中断）

| 步骤 | 状态 | 说明 |
|------|------|------|
| patterns/ 目录创建 | ✅ 存在 | `iter2/patterns/` 目录已建，说明进入了 iter2 |
| 其余步骤 | ❌ 未完成 | 中断后无缓存 |

---

## 重启前必须执行的修复

```bash
cd /Users/zhongyiliu/Desktop/data_agent/DAComp/experience_evolution

# 1. 删除 cards_written checkpoint（否则 pipeline 跳过写卡但 index 是空的）
rm exp_v5/iter1/cards_written.json

# 2. 创建 iter1 complete 标记（告知 pipeline iter1 已完成，直接从 iter2 开始）
#    先查看 evolution_log.json 中 iter1 的实际结果
cat exp_v5/evolution_log.json
```

**如果 iter1 结果为 KEEP（delta > -2pp）：**
```bash
# 手动创建 iter_complete.json，让 pipeline 跳过 iter1 直接跑 iter2
python3 -c "
import json, os
from pathlib import Path
idir = Path('exp_v5/iter1')
rec = {
    'iteration': 1,
    'agent_results_dir': str(Path('$(pwd)/../methods/da-agent/output/deepseek-v3.2-evolve_exp_v5_iter1_r2').resolve()),
    'new_scores_csv': '',  # 需根据实际情况填写
    'kept': True,
}
(idir / 'iter_complete.json').write_text(json.dumps(rec, indent=2))
print('Written iter_complete.json')
"
```

**如果直接重跑 iter1（最简单）：**
```bash
# 只删 cards_written，其余 checkpoint 保留，pipeline 会：
# - 跳过：模式提取、合成、guard（有缓存）
# - 重跑：写卡 → r0 → r1 → r2 → judge → 评分
rm exp_v5/iter1/cards_written.json
```

---

## 重启命令

```bash
cd /Users/zhongyiliu/Desktop/data_agent/DAComp/experience_evolution
export BAILIAN_API_KEY='sk-bc44390720ff44618c73c5020588aaed'

nohup /Users/zhongyiliu/anaconda3/envs/dacomp/bin/python evolve_pipeline.py \
  --mode auto \
  --run exp_v5 \
  --case-file exp_v4_60cases/case_list_60.txt \
  --n-cases 15 \
  --test-n 10 \
  --n-runs-per-case 3 \
  --max-iterations 3 \
  --agent-timeout-minutes 10 \
  --max-workers 8 \
  >> exp_v5_pipeline.log 2>&1 &

echo "PID=$!"
```

---

## 7 张已合成的卡（synthesis_cache 中）

来自 `exp_v5/iter1/synthesis_cache.json`（`synthesized_cards` 字段）：

1. Define and expand analysis dimensions early
2. Formalize hypothesis testing for comparative analyses
3. Operationalize findings into actionable recommendation matrices
4. *(更多见 synthesis_cache.json)*

源 case：dacomp-058, 060, 048, 069, 022, 035, 070, 098, 078, 029, 076, 094, 066, 027, 090

---

## 注意事项

- `exp_v5/cards/index.json` 目前为空——重启后写卡步骤会重建它
- iter2 的 `patterns/` 目录已存在但为空，重启时 iter2 会正常从提取模式开始
- `--n-runs-per-case 3` 意味着每次 iter 的 agent 阶段 = 3 × 10 = 30 次推理
- baseline_csv 固定为 `dacomp-da/evaluation_suite/model_scores/deepseek-v3.2-baseline__*.csv`，不要修改
