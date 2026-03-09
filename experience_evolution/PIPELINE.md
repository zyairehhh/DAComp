# Experience Card 自演进 Pipeline 算法文档

## 目录结构

```
DAComp/
├── dacomp-da/
│   ├── experience_cards/        卡片仓库（index.json + cards/*.md）
│   └── tasks/dacomp-da.jsonl    100 个测试 case
├── experience_evolution/        本 pipeline 目录
│   ├── pipeline_state.py        断点恢复 checkpoint I/O
│   ├── retrieval.py             混合检索模拟（关键词 + 语义 embedding）
│   ├── regression_guard.py      预写入回退保护 + 覆盖率上限 + surgical rollback
│   ├── classify_failures.py     失败根因分类（4 种类型）
│   ├── case_state.py            Stagnation 追踪（hard case 标记）
│   ├── card_utils.py            卡片 I/O、置信度计算、零命中剪枝、rollback 工具
│   ├── select_cases.py          选最差 cases（按 weighted_total_score 排序）
│   ├── extract_patterns.py      LLM 提取失败 pattern
│   ├── synthesize_cards.py      LLM 合成新 experience card
│   ├── evolve_pipeline.py       主流程编排
│   └── <run_name>/              --run 模式下的运行目录
│       ├── iter1/               断点文件（按 iteration 隔离）
│       │   ├── patterns/        per-case pattern 缓存
│       │   ├── synthesis_cache.json
│       │   ├── guard_cache.json
│       │   ├── cards_written.json
│       │   ├── averaged_scores.csv   （--n-runs-per-case > 1 时生成）
│       │   └── iter_complete.json
│       ├── iter2/
│       │   └── ...
│       ├── cards/               本次 run 的 experience cards
│       ├── case_state.json
│       └── evolution_log.json
└── methods/da-agent/            DA-Agent 推理入口
```

---

## 一次迭代的完整流程

| 阶段 | 函数 | 说明 | 是否调用 LLM |
|------|------|------|:---:|
| **前置加载** | — | 读取 instructions / scores / baseline_weighted / index / case_state | 否 |
| **Step 0.5** 剪枝 | `prune_disabled_cards()` + `prune_zero_hit_cards()` | 删除 priority=0 的失效卡；再删除在全量 corpus 中命中 0 次的自动生成死重卡 | 否 |
| **Step 1** 选 Case | `select_worst_cases()` | 按 `weighted_total_score` 升序选 N 个最差 case，排除已标记为 hard 的 case | 否 |
| **Step 2a** 失败分类 | `classify_failure_type()` | LLM 判断失败根因（结果缓存），仅 `experience_gap` 继续提取 | 是（max_tokens=512） |
| **Step 2b** Pattern 提取 | `extract_patterns_for_case()` | LLM 从轨迹 + rubrics 中提取可复用的分析原则；可选附加对比成功 case | 是 |
| **Step 3** 合成候选卡 | `synthesize_cards_with_llm()` | 先做 Jaccard dedup gate 过滤近重复 pattern，再由 LLM 合并为 3-8 张最终候选卡 | 是 |
| **Step 4** 预写入保护 | `run_pre_write_guard()` | ① 检索 diff → at-risk 检测 → 关键词收紧；② 覆盖率上限（>15% corpus）→ 收紧或 block | 否 |
| **Step 5** 人工审核 | `interactive_review()` | 仅 `interactive` 模式：逐卡展示并等待用户批准 / 跳过 | — |
| **Step 6** 写入卡片 | `write_new_cards()` + embedding | 写 `.md`，原子更新 `index.json`；初始 confidence=0.3，priority=3；**写入后立即计算 embedding 并存入 index** | 否（Embedding API）|
| **Step 6.5** 检索验证 | `validate_new_cards()` | 确认每张新卡能被测试集中至少一个 case 检索到，0 命中则打 WARN | 否 |
| **Step 6+7** Agent 推理 × N | `run_agent_on_cases()` | 循环 N 次（`--n-runs-per-case`），每次不同 suffix；超时 case 排除 | 否 |
| **Step 7** LLM 评分 × N | `run_llm_judge()` | 每轮 agent 结果分别评分；N > 1 时生成 `averaged_scores.csv` 取均值 | 是 |
| **Step 8** 比较 + 更新 | `compare_scores()` | 用均值 CSV 计算 per-case delta；更新卡置信度；更新 stagnation 状态 | 否 |
| **Step 9a** Surgical Rollback | `find_culprit_cards()` | 对 baseline > 60 且 delta < -15pp 的 case，定位并删除罪魁新卡 | 否 |
| **Step 9b** 全量兜底 | `rollback_cards()` | 若平均 delta < -2pp，删除本轮所有剩余新卡 | 否 |
| **记录日志** | `_log_iteration()` | 写入 `evolution_log.json` | 否 |

---

## Step 0.5：前置剪枝

每轮迭代开始时自动执行，不需要手动触发。

### prune_disabled_cards（已有）
删除 `priority=0`（置信度衰减后被禁用）的自动生成卡，同时删除对应 `.md` 文件。手工卡（`confidence=1.0`）永不删除。

### prune_zero_hit_cards（新增）
扫描所有自动生成卡（`confidence < 1.0`）在**全量 100 个 task** 上的检索命中数。命中数为 0 的卡属于纯死重（keywords 与任何 task 不匹配），直接删除。

```python
prune_zero_hit_cards(index, cards_dir, all_instructions)
→ (updated_index, pruned_ids)
```

---

## Step 4：预写入保护（`run_pre_write_guard`）

**此步骤完全无 LLM 调用**，全部为纯字符串运算。

### 4a. At-risk 检测（原有逻辑）

1. 模拟写入前/后检索 diff → 找到新卡会被注入的 case
2. 触发条件：**有新卡被新增注入** AND **baseline > 60**
3. 对触发 case 的候选卡尝试 `tighten_keywords()`：移除"命中 at-risk 但不命中 source"的非判别性关键词
4. 收紧后剩余 < 3 个关键词 → 放弃收紧，记录 WARN

### 4b. 覆盖率上限检查（新增）

**阈值：** `MAX_COVERAGE_FRACTION = 0.15`（新卡最多匹配 15% 的 task corpus）

流程：
1. 对每张候选卡调用 `_coverage_fraction(card, all_instructions)`，计算命中率
2. 命中率 > 15% → 过宽，尝试 `tighten_keywords()`（使用所有非 source case 作 at-risk）
3. 收紧后仍 > 15% → 加入 `blocked_card_ids`，**不写入 index**
4. 收紧成功 → 使用收紧后的卡继续流程

`run_pre_write_guard` 新增参数：
```python
run_pre_write_guard(
    candidate_cards, current_index, tasks, baseline_scores,
    all_instructions=instructions,     # 新增：用于覆盖率检查
    max_coverage_fraction=0.15,        # 新增：覆盖率上限
)
```

---

## Step 6：写入卡片 + Embedding 存储

写入后立即为新卡计算语义向量并持久化到 `index.json`：

```python
# embed text = when_to_use + title（与推理时 experience.py 的查询向量口径一致）
texts = [f"{card['when_to_use']} {card['title']}" for card in new_cards]
vecs  = get_embeddings(texts)   # 单次 batch API 调用
# 写回 index.json: card["embedding"] = vec
```

- 使用 DashScope `text-embedding-v3`，维度 1024
- 无 `BAILIAN_API_KEY` 时静默跳过（fallback 到纯关键词检索）
- 旧卡没有 `embedding` 字段，自动 fallback

---

## Step 6+7：多次运行取均值（`--n-runs-per-case`）

**默认 N=1**（与旧版完全兼容）。N>1 时：

```
for run_idx in range(N):
    suffix = f"evolve_{run}_iter{i}_r{run_idx}"
    run_agent_on_cases(...)  → agent_results_dir
    run_llm_judge(...)       → run_csv
averaged_scores.csv = _write_averaged_csv(run_csvs, completed_case_ids)
```

- 每次使用不同 suffix，产生独立输出目录
- `completed_case_ids` 取所有轮次的并集
- Step 8 使用 `averaged_scores.csv` 做 delta 比较，降低 agent 随机性噪声
- 推荐 N=3，与 `--test-n 10` 配合：10×3=30 次推理，统计标准误差 ±6pp

---

## 检索评分算法（混合检索，`retrieval.py`）

**从 pure keyword 升级为 Hybrid（语义 + 关键词）：**

```
final_score = α × semantic_score + (1-α) × keyword_score_norm
α = SEMANTIC_ALPHA = 0.7
```

### 关键词得分（keyword_score，原有）

| 组件 | 计算方式 | 分值 |
|------|----------|------|
| 多词关键词命中 | token 短语完整出现 | +2.0 |
| 单词关键词命中 | 单 token 出现 | +1.0 |
| 组合奖励 | ≥3 关键词 AND ≥1 标签命中 | +2.0 |
| 标签命中 | tag token 出现 | +0.5/tag |
| 语义重叠 bonus | (when_to_use+title) token 重叠×3.0，上限 1.5 | 0~1.5 |

### 语义得分（semantic_score，新增）

```python
sem_sim   = cosine_similarity(task_embedding, card_embedding)  # [-1, 1]
sem_score = max(0, sem_sim) * 5.0   # 映射到 [0, 5]
kw_norm   = min(keyword_score, 10) / 10 * 5.0   # 归一化到 [0, 5]
final     = 0.7 * sem_score + 0.3 * kw_norm
```

- 卡片 embedding 存在 `index.json` 的 `"embedding"` 字段（写卡时计算）
- 无 embedding 字段的卡自动 fallback 到 `final = keyword_score`
- 推理时（`experience.py`）对 task instruction 实时调用 embedding API（单次，非 batch）

### 过滤规则

1. `priority == 0` → 跳过
2. `score < MIN_RETRIEVAL_SCORE (3.0)` → 过滤
3. `score < best_score × 0.5` → 过滤
4. 最多返回 top-k = 4 张

### 公共函数

```python
# pipeline 仿真（batch embedding 可选）
simulate_retrieval_map(cards, tasks, top_k=4, use_embeddings=False)
  → {case_id: [retrieved_card_id, ...]}

# batch embedding（DashScope API）
get_embeddings(texts)
  → List[List[float]]   # 失败返回空向量列表，graceful fallback

# 验证新卡检索覆盖
validate_new_cards(new_card_ids, test_case_ids, cards_dir, instructions)
  → {card_id: [hit_case_ids]}
```

---

## 关键常量汇总

| 常量 | 值 | 含义 | 所在文件 |
|------|----|------|---------|
| `MIN_RETRIEVAL_SCORE` | 3.0 | 最低检索分（绝对阈值） | retrieval.py |
| `DEFAULT_TOP_K` | 4 | 每次最多检索卡数 | retrieval.py |
| `SEMANTIC_ALPHA` | 0.7 | 语义权重（1-α=0.3 为关键词权重） | retrieval.py |
| `_EMBEDDING_MODEL` | text-embedding-v3 | DashScope 嵌入模型 | retrieval.py |
| `_EMBEDDING_DIM` | 1024 | 向量维度 | retrieval.py |
| `MAX_COVERAGE_FRACTION` | 0.15 | 新卡最大 corpus 命中率 | regression_guard.py |
| `HIGH_BASELINE_THRESHOLD` | 60.0 | Surgical rollback 触发的 baseline 分 | regression_guard.py |
| `CASE_REGRESSION_THRESHOLD` | -15.0 | Surgical rollback 触发的 per-case delta | regression_guard.py |
| `IMPROVEMENT_THRESHOLD` | 0.02 | 置信度提升触发的 avg delta（fractions） | card_utils.py |
| `REGRESSION_THRESHOLD` | -0.02 | 全量 rollback 触发的 avg delta | card_utils.py |
| `CONFIDENCE_GENERATED` | 0.3 | 新卡初始置信度 | card_utils.py |
| `CONFIDENCE_HANDCRAFTED` | 1.0 | 手工卡置信度（永不自动删除） | card_utils.py |
| `stagnation_threshold` | 3 | 连续多少轮无改善 → 标记为 hard | case_state.py |

---

## 置信度 → 优先级映射

| confidence | priority | 效果 |
|-----------|---------|------|
| ≥ 0.8 | 5 | 强优先检索 |
| ≥ 0.5 | 4 | 正常检索 |
| ≥ 0.2 | 3 | 正常检索（新卡默认） |
| < 0.2 | **0** | **禁止检索（disabled，下轮剪枝删除）** |

更新规则（per card，基于 `avg_delta_frac` of hit cases）：
- `delta > +2%` → `+0.2`（上限 1.0）
- `delta < -2%` → `-0.3`（下限 0.0）

---

## Multi-Iteration 断点恢复

**轮级断点：** `iter{N}/iter_complete.json` 存在 → 跳过该轮，从 `agent_results_dir`/`new_scores_csv` 字段重建 `prev_result`

**步骤级断点：**

| 步骤 | 缓存文件 | 命中时行为 |
|------|---------|-----------|
| Step 3 合成 | `iter{N}/synthesis_cache.json` | 跳过 LLM，加载缓存 |
| Step 4 Guard | `iter{N}/guard_cache.json` | 跳过检索模拟 |
| Step 6 写卡 | `iter{N}/cards_written.json` | 跳过写入，使用已记录 added_ids |

**两个 CSV 的区别：**

| CSV | 用途 | 是否随轮变化 |
|-----|------|-------------|
| `baseline_csv` | delta 对比基准（guard 阈值、rollback 判断） | **固定不变** |
| `extract_csv` | pattern 提取时的 rubrics row | 首轮用 baseline，后续轮用上轮输出 |

---

## CLI 参数速查

```bash
python evolve_pipeline.py \
  --mode            interactive|auto|dry-run \
  --n-cases         15          # 提取 pattern 的 case 数量（建议 10-20）
  --test-n          10          # 跑 agent + 评分的 case 数量
  --n-runs-per-case 3           # 每个 test case 独立运行次数，取均值降噪（默认 1）
  --iteration       1           # 起始 iteration 编号
  --max-iterations  3           # auto 模式最大轮数
  --baseline-csv    <path>      # 固定基准 CSV（不随轮次更新）
  --traj-dir        <path>      # agent 轨迹目录（用于首轮 pattern 提取）
  --cards-dir       <path>      # experience_cards 目录
  --case-file       <path>      # 指定 case 列表（跳过自动排序）
  --run             <name>      # 运行目录名（创建 <name>/iter{N}/ 存放 checkpoint）
  --max-workers     8           # agent + judge 并发数
  --agent-timeout-minutes 10    # 单 case 推理超时（分钟），0=无限制
  --skip-agent-run              # 只写卡不跑 agent（快速验证）
  --force-extract               # 强制重提取（忽略已有缓存）
  --use-contrast                # 启用对比学习（附加相似成功 case）
```

**推荐正式运行配置：**
```bash
nohup python evolve_pipeline.py \
  --mode auto --run exp_v5 \
  --case-file exp_v4_60cases/case_list_60.txt \
  --n-cases 15 --test-n 10 --n-runs-per-case 3 \
  --max-iterations 3 --agent-timeout-minutes 10 --max-workers 8 \
  > exp_v5_pipeline.log 2>&1 &
```
