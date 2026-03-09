# DAComp Evolution Pipeline — AI Agent Quick Reference

> 本文档为 AI agent（Claude Code）专用，密度优先，方便快速定位代码和理解决策上下文。
> 人类可读版见 PIPELINE.md。

---

## 项目一句话

DAComp 是一个 100-case 数据分析 benchmark。DA-Agent 在推理时从 `experience_cards/index.json` 检索相关"经验卡"注入 prompt。本 pipeline 自动发现 agent 失败的原因、合成新卡、测试效果、决定是否保留。

---

## 关键路径

```
DAComp/
├── dacomp-da/
│   ├── tasks/dacomp-da.jsonl                # 100 cases，instance_id: dacomp-001~100
│   ├── experience_cards/                    # 【生产卡库】agent 推理时读这里
│   │   ├── index.json                       # 卡片元数据（含 embedding 向量）
│   │   └── cards/*.md                       # 卡片正文
│   └── evaluation_suite/
│       ├── model_scores/
│       │   └── deepseek-v3.2-baseline__*.csv  # 基准分（固定，勿覆盖）
│       └── baseline_agent_results/deepseek-v3.2-baseline/  # 基准轨迹
├── experience_evolution/                    # 【本 pipeline】
│   ├── evolve_pipeline.py                   # 主流程（从这里看全局）
│   ├── retrieval.py                         # 检索模拟（keyword+semantic hybrid）
│   ├── regression_guard.py                  # 写卡前保护（at-risk + 覆盖率上限）
│   ├── card_utils.py                        # 卡片 I/O、置信度、剪枝、rollback
│   ├── synthesize_cards.py                  # LLM 合成卡片（含 write_new_cards）
│   ├── extract_patterns.py                  # LLM 提取失败 pattern
│   ├── classify_failures.py                 # LLM 失败分类（experience_gap 才提取）
│   ├── pipeline_state.py                    # checkpoint 读写（断点恢复）
│   ├── case_state.py                        # stagnation 追踪（hard case 标记）
│   ├── select_cases.py                      # 选 worst cases
│   └── exp_v*/                              # 实验运行目录（iter1/2/3 + cards/）
└── methods/da-agent/
    ├── run_parallel.py                      # agent 推理入口
    ├── da_agent/agent/experience.py         # 推理时检索逻辑（必须与 retrieval.py 同步）
    └── output/                              # 推理输出（final_summary.json + result.json）
```

---

## 运行一个实验的最简命令

```bash
cd /Users/zhongyiliu/Desktop/data_agent/DAComp/experience_evolution
export BAILIAN_API_KEY='sk-bc44390720ff44618c73c5020588aaed'

nohup python evolve_pipeline.py \
  --mode auto --run exp_v5 \
  --case-file exp_v4_60cases/case_list_60.txt \
  --n-cases 15 --test-n 10 --n-runs-per-case 3 \
  --max-iterations 3 --agent-timeout-minutes 10 --max-workers 8 \
  > exp_v5_pipeline.log 2>&1 &
```

**查看进度：** `tail -f exp_v5_pipeline.log`

**查看 agent 推理进程：** `pgrep -fl run_parallel`

---

## 重要变量和常量

| 变量/常量 | 值 | 文件 | 说明 |
|---|---|---|---|
| `BAILIAN_API_KEY` | env var | — | DashScope API key（LLM + embedding） |
| `DEFAULT_TOP_K` | 4 | retrieval.py | 每次检索最多返回 4 张卡 |
| `MIN_RETRIEVAL_SCORE` | 3.0 | retrieval.py | 检索分低于此值不返回 |
| `SEMANTIC_ALPHA` | 0.7 | retrieval.py | 混合检索中语义权重 |
| `MAX_COVERAGE_FRACTION` | 0.15 | regression_guard.py | 新卡命中 >15% corpus 则收紧/block |
| `HIGH_BASELINE_THRESHOLD` | 60.0 | regression_guard.py | baseline > 60 的 case 受 surgical rollback 保护 |
| `CASE_REGRESSION_THRESHOLD` | -15.0 | regression_guard.py | per-case delta < -15pp 触发 surgical rollback |
| `CONFIDENCE_GENERATED` | 0.3 | card_utils.py | 新卡初始置信度 |
| `CONFIDENCE_HANDCRAFTED` | 1.0 | card_utils.py | 手工卡置信度，永不自动删除 |
| `REGRESSION_THRESHOLD` | -0.02 | card_utils.py | 平均 delta < -2pp 触发全量 rollback |
| `_SCORE_COLUMN` | `weighted_total_score` | evolve_pipeline.py | CSV 中用于比较的列名 |

---

## index.json 卡片字段

```jsonc
{
  "id": "exp-da-001",
  "title": "...",
  "path": "cards/exp-da-001-xxx.md",
  "when_to_use": "...",       // 检索 overlap 计算用
  "keywords": ["...", "..."], // 关键词匹配（≥3 个）
  "tags": ["..."],            // 标签加分
  "priority": 3,              // 0=disabled, 3-5=active
  "confidence": 0.3,          // 0.0-1.0，手工卡=1.0
  "embedding": [...],         // 1024-dim float，新卡写入时计算；旧卡无此字段→fallback
  "source_cases": ["dacomp-XXX"],  // 来源 case（guard 用）
  "added_in_iteration": "iter1"    // 写入轮次（traceability）
}
```

---

## 置信度生命周期

```
新卡写入: confidence=0.3, priority=3
测试结果好 (+2pp): confidence += 0.2 → 0.5, priority=4
测试结果差 (-2pp): confidence -= 0.3 → 0.0, priority=0 → 下轮被 prune_disabled_cards 删除
手工卡: confidence=1.0 → 永不自动删除
```

---

## 检索算法（pipeline 仿真 ≡ 推理时行为）

**两个文件必须保持同步：**
- `experience_evolution/retrieval.py`（pipeline 仿真）
- `methods/da-agent/da_agent/agent/experience.py`（推理时）

**Hybrid 评分：**
```
final_score = 0.7 × semantic_score + 0.3 × keyword_score_norm

semantic_score  = max(0, cosine(task_emb, card_emb)) × 5.0
keyword_score_norm = min(keyword_score, 10) / 10 × 5.0

# 无 embedding 时：final_score = keyword_score（fallback）
```

**keyword_score 各组件：**
- 多词关键词命中：+2.0
- 单词关键词命中：+1.0
- ≥3 关键词 AND ≥1 标签同时命中：+2.0 组合奖励
- 每个标签 token 命中：+0.5
- when_to_use+title 与任务 token 重叠 × 3.0（上限 1.5）

---

## Agent 推理调用

```bash
cd methods/da-agent
python run_parallel.py \
  --model deepseek-v3.2 \
  -s <suffix> \
  --example_index 0,1,2,...  # 0-based，dacomp-001=0
  --use_experience \
  --max_steps 80 \
  -w 8 \
  --experience_dir <cards_dir>  # 不传则用默认 /workspace/_aux/experience_cards
```

**steps 统计（exp_v4_60cases iter3，60 cases）：** 均值 53.6，中位数 54，21.5% 重复步骤。

---

## 分数体系

| 列名 | 含义 | pipeline 使用 |
|------|------|--------------|
| `weighted_total_score` | 加权总分（rubrics+GSB），主指标 | delta 比较、guard 阈值 |
| `rubrics_percentage` | rubrics 子项均值百分比 | 置信度更新（per-card） |

Rubrics：Completeness、Accuracy、Conclusiveness（各 0-1，加权）
GSB：Readability、Professionalism、Visualization（-1/0/+1 相对比较）

---

## 常见问题速查

| 问题 | 排查位置 |
|------|---------|
| 新卡从未被检索到 | `validate_new_cards` 输出；检查 keywords 是否在 task 中出现 |
| 卡片覆盖率过高被 block | `regression_guard.py` BLOCKED 日志；降低 keywords 中的泛化词 |
| 推理进程卡住 | `pgrep -fl run_parallel`；检查 `--agent-timeout-minutes` |
| 断点恢复失败 | 检查 `iter{N}/` 下缓存文件；删除对应 `*_cache.json` 强制重跑该步骤 |
| delta 信号不可靠 | 增大 `--n-runs-per-case`（推荐 3）；减小 `--test-n` 但保持 3 runs |
| embedding API 失败 | 检查 `BAILIAN_API_KEY`；fallback 到纯关键词，不影响流程 |

---

## 实验历史

| 实验 | Cases | 结果 | 状态 |
|------|-------|------|------|
| exp_v4_60cases/iter1 | 60 | +2.1pp KEEP | 完成 |
| exp_v4_60cases/iter2 | 60 | -1.97pp KEEP（含 surgical rollback） | 完成 |
| exp_v4_60cases/iter3 | 60 | -2.37pp ROLLBACK | 完成 |
| **exp_v5/iter1** | **15n/10t×3r** | **进行中** | **🔄 running** |

**iter2/3 退步根因：** 26 个"持续负向" case 中 14 个检索 0 张卡但仍退步 10-40pp → 评估噪声 (±20pp) >> 卡片信号 (±5pp)。解法：多次运行均值。

**优化历史（当前代码版本已包含）：**
1. `--n-runs-per-case N`：多次运行均值降噪
2. `prune_zero_hit_cards`：零命中死重卡自动删除
3. 覆盖率上限（>15% corpus）：防止过宽卡干扰
4. Hybrid embedding 检索：语义 0.7 + 关键词 0.3

---

## 修改代码时的注意事项

1. **`retrieval.py` 和 `experience.py` 必须同步**：任何检索逻辑变更都要同时改两处
2. **`card_utils.py` 所有函数返回新对象，不原地修改**：遵循 immutable 约定
3. **`index.json` 写入必须用 `save_index()`（原子 write→rename）**：不要直接 `open(..., 'w')`
4. **手工卡（confidence=1.0）任何自动剪枝逻辑都不能删除**
5. **baseline_csv 始终固定**：只有手动更换基准时才改，不能被 pipeline 覆盖
