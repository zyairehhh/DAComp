# Experience Card 自演进 Pipeline 算法文档

## 目录结构

```
DAComp/
├── dacomp-da/
│   ├── experience_cards/        卡片仓库（index.json + cards/*.md）
│   └── tasks/dacomp-da.jsonl    100 个测试 case
├── experience_evolution/        本 pipeline 目录
│   ├── retrieval.py             纯字符串检索模拟（无 LLM）
│   ├── regression_guard.py      预写入回退保护 + surgical rollback
│   ├── classify_failures.py     失败根因分类（4 种类型）
│   ├── case_state.py            Stagnation 追踪（hard case 标记）
│   ├── card_utils.py            卡片 I/O、置信度计算、rollback 工具
│   ├── select_cases.py          选最差 cases（按 weighted_total_score 排序）
│   ├── extract_patterns.py      LLM 提取失败 pattern
│   ├── synthesize_cards.py      LLM 合成新 experience card
│   ├── evolve_pipeline.py       主流程编排
│   └── patterns/                LLM 输出缓存目录（per-case JSON）
└── methods/da-agent/            DA-Agent 推理入口
```

---

## 一次迭代的完整流程

| 阶段 | 函数 | 说明 | 是否调用 LLM |
|------|------|------|:---:|
| **前置加载** | — | 读取 instructions / scores / baseline_weighted / index / case_state | 否 |
| **Step 1** 选 Case | `select_worst_cases()` | 按 `weighted_total_score` 升序选 N 个最差 case，排除已标记为 hard 的 case | 否 |
| **Step 2a** 失败分类 | `classify_failure_type()` | LLM 判断失败根因（结果缓存），仅 `experience_gap` 继续提取；`factual_gap`/`factual_error` 路由到知识库管道（当前跳过） | 是（max_tokens=512） |
| **Step 2b** Pattern 提取 | `extract_patterns_for_case()` | LLM 从轨迹 + rubrics 中提取可复用的分析原则；可选附加对比成功 case | 是 |
| **Step 3** 合成候选卡 | `synthesize_cards_with_llm()` | 先做 Jaccard dedup gate 过滤近重复 pattern，再由 LLM 合并为 3-8 张最终候选卡 | 是 |
| **Step 4** 预写入保护 | `run_pre_write_guard()` | 模拟写入前后的检索 diff，对会影响高分 case（baseline > 60）的候选卡自动收紧关键词 | **否** |
| **Step 5** 人工审核 | `interactive_review()` | 仅 `interactive` 模式：逐卡展示并等待用户批准 / 跳过 | — |
| **Step 6** 写入卡片 | `write_new_cards()` | 写 `.md` 文件，原子更新 `index.json`；初始 confidence=0.3，priority=3 | 否 |
| **Step 6.5** 检索验证 | `validate_new_cards()` | 确认每张新卡能被测试集中至少一个 case 检索到，0 命中则打 WARN | 否 |
| **Step 7** Agent 推理 | `run_agent_on_cases()` | 以 `--use_experience` 跑 DA-Agent（上限 80 步，4 并发），导出轨迹 | 否 |
| **Step 8** LLM 评分 | `run_llm_judge()` | 对 Agent 输出打 Rubrics + GSB 分，生成 `new_scores.csv` | 是 |
| **Step 9** 比较 + 更新 | `compare_scores()` | 计算 per-case `weighted_total_score` delta；更新卡置信度；更新 stagnation 状态 | 否 |
| **Step 10a** Surgical Rollback | `find_culprit_cards()` | 对 baseline > 60 且 delta < -15pp 的 case，模拟定位并删除罪魁新卡，保留其余 | 否 |
| **Step 10b** 全量兜底 | `rollback_cards()` | 若平均 delta < -2pp，删除本轮所有剩余新卡，保证整体不退步 | 否 |
| **记录日志** | `_log_iteration()` | 将本轮 added_ids / per-case delta / kept 状态写入 `evolution_log.json` | 否 |

> **注：** Step 4（guard）在代码日志里打印为 `[Step 4.5]`，Step 5（interactive）打印为 `[Step 4]`，这是历史遗留的标注顺序问题，实际执行顺序以本表为准。

---

## 前置数据加载

`run_pipeline()` 在所有 step 前加载共享数据：

| 变量 | 来源 | 用途 |
|------|------|------|
| `instructions` | `dacomp-da.jsonl` | `{instance_id: instruction}`，100 条 |
| `scores_by_id` | `extract_csv`（首轮为 baseline CSV，多轮时为上轮输出 CSV） | pattern 提取时的 rubrics row |
| `baseline_weighted` | baseline CSV（始终固定） | guard 阈值 + rollback delta 比较 |
| `index` | `experience_cards/index.json` | 现有卡片元数据 |
| `existing_summary` | `summarize_existing_cards(index)` | 传入 LLM，避免重复提取 |
| `case_state` | `case_state.json` | stagnation 追踪，hard case 排除 |

---

## Step 1：选 Case

**函数：** `select_worst_cases(baseline_csv, n, sort_by="weighted_total_score")`

`weighted_total_score` 是 benchmark 自带的加权综合分（rubrics + GSB），是衡量 experience card 整体效果的主指标。

**流程：**

1. 读取 baseline CSV，按 `weighted_total_score` **升序**排列所有 case
2. 从 `case_state.json` 获取 `hard_ids`（stagnation_count ≥ 3 的 case）
3. 先取 `n + len(hard_ids)` 个最差 case，然后过滤掉 `hard_ids`，最终取前 `n` 个
4. 其中前 `test_n` 个作为本轮测试集（Step 7 跑 agent，Step 8 评分）

**可选：** `--case-file` 直接指定 case 列表，跳过自动排序。

---

## Step 2：失败分类 + Pattern 提取

每个 case 依次执行两步：**分类**（决定是否提取）→ **提取**（生成候选 pattern）。

### Step 2a. 失败根因分类（`classify_failure_type`）

**缓存机制：** 先读 `patterns/{iid}_failure_type.json`，命中则直接使用，不重复调用 LLM。

**LLM 调用参数：** `max_tokens=512`，`temperature=0.0`，最多重试 3 次。

**Prompt 内容：**
- task instruction（前 2000 字符）
- rubrics 失败摘要（score ≤ 0.5 的 criteria，前 2000 字符）
- agent 轨迹的最后 3000 字符

**失败类型及处理：**

| 类型 | 含义 | 后续操作 |
|------|------|----------|
| `experience_gap` | agent 缺乏可复用的分析技能/经验（含方法论错误、遗漏校验步骤、忽略边界情况等），经验卡可修复 | **继续提取** |
| `factual_gap` | 分析步骤正确但缺失领域事实（行业标准、阈值定义等），需补充到知识库 | 跳过（不提取经验卡） |
| `factual_error` | agent 使用了错误的领域知识（KB 条目有误或模型幻觉），需修正知识库现有条目 | 跳过（不提取经验卡） |
| `execution_error` | 代码报错 / 工具崩溃 / 无输出 | 跳过 |
| `data_limitation` | 数据本身不足，任务本身不可解 | 跳过 |
| `ambiguous_task` | 任务说明有歧义 | 跳过 |

**失败兜底：** LLM 调用失败或解析出错时，默认返回 `experience_gap`（宁多提取，不漏掉可修的 case）。

---

### Step 2b. Pattern 提取（`extract_patterns_for_case`）

**跳过条件：** `patterns/{iid}_patterns.json` 已存在（且未指定 `--force-extract`）。

**轨迹截断策略（`_truncate_trajectory`）：**
保留前 12 个 step + 后 25 个 step，中间部分用省略号替代，避免 prompt 过长。

**Rubrics 失败分析（`_extract_failure_analyses`）：**
- 递归遍历 `rubrics_result` JSON（去掉 markdown 代码块包裹）
- 筛选 `score ≤ 0.5` 或含失败关键词（"did not", "missing", "failed" 等）的 criteria
- 按 score 升序（最差的优先），累积到 12000 字符上限

**Prompt 构成：**
1. task instruction（前 3000 字符）
2. 截断后的 agent 轨迹（前 20000 字符）
3. rubrics 评分百分比 + 失败分析
4. 现有卡片摘要（告知 LLM 哪些已存在，避免重复）
5. （可选）对比成功 case（见下方对比学习）

**LLM 输出：** JSON 数组，每个 pattern 包含 `title`、`when_to_use`、`experience`、`checklist`、`common_failure_prevented`、`keywords`、`tags`、`source_criterion`。

**输出：** 写入 `patterns/{iid}_patterns.json`，同时在每个 pattern 中注入 `source_case: iid`。

#### 对比学习（`--use-contrast`）

启用后，对每个失败 case 额外附加 top-3 相似高分 case 作对比：

1. 在所有 instructions 中筛选 `rubrics_pct ≥ 70%` 的 case
2. 计算各 case instruction 与目标 case 的 Jaccard token 重叠比
3. 取重叠最高的 3 个，拼接为「Similar Successful Cases」段落追加到 prompt 末尾
4. 引导 LLM 对比成功/失败做法，提取更精准的 pattern

---

## Step 3：合成候选卡

**函数：** `synthesize_cards_with_llm(all_patterns, existing_summary)`

### 3a. Jaccard Dedup Gate（预过滤）

在 LLM 合成之前，先做纯字符串去重：

- 对每个 pattern 的 `when_to_use` 字段做 token 化（小写字母+数字）
- 计算与 `existing_summary`（现有所有卡的摘要文本）的 Jaccard 重叠比
- **阈值 0.85**：重叠超过此值 → 视为与现有卡重复，过滤掉
- 过滤后仍为空 → 直接返回，不调用 LLM

### 3b. LLM 合并

**Prompt 内容：**
- 现有卡片摘要（勿重复）
- 所有候选 pattern（JSON，超过 40000 字符则截断）
- 来源 case 数量和 pattern 总数

**合并规则（prompt 内指令）：**
1. 将表达同一底层原则的 pattern 分组
2. 每组输出一张最终卡（取最优表述）
3. 跳过已被现有卡覆盖的 pattern
4. 目标质量：3-8 张，少而精

**LLM 输出：** JSON 数组，每张卡包含 `title`、`when_to_use`、`experience`、`checklist`、`common_failure_prevented`、`keywords`（≥3 个）、`tags`、`source_cases`。

---

## Step 4：预写入保护（`run_pre_write_guard`）

**目标：** 在任何文件落盘前，检测关键词过宽的候选卡，防止它们在推理时被注入到与其内容无关的高分 case 中。

**此步骤完全无 LLM 调用**，全部为纯字符串运算。

### 流程

**1. 为候选卡分配临时 ID（pipeline 中）**

在调用 guard 前，`evolve_pipeline.py` 先为所有候选卡分配临时 ID（`exp-da-NNN`），以便检索模拟能区分各卡。

**2. 模拟检索（before）**

对全量 100 个 case 模拟检索，使用**现有卡**（不含候选卡）：
```
before_map = simulate_retrieval_map(current_index, tasks)
```

**3. 模拟检索（after）**

合入候选卡后再次模拟：
```
after_map = simulate_retrieval_map(current_index + candidate_cards, tasks)
```

**4. Diff**

找出检索结果发生变化的 case（`added`/`removed`）。

**5. At-risk 检测（`flag_at_risk_cases`）**

触发条件：该 case **有新卡被新增注入** AND **baseline `weighted_total_score` > 60**

按 baseline 分降序排列，分越高的 case 越优先保护。

**6. 关键词收紧（`tighten_keywords`）**

对每张触发 at-risk 的候选卡：
- 对每个关键词 `kw`：
  - `hits_at_risk`：`kw` 是否出现在任意 at-risk case 的 instruction 中
  - `hits_source`：`kw` 是否出现在该卡的 `source_cases` instruction 中
  - 若 `hits_at_risk AND NOT hits_source` → 非判别性词，加入移除列表
- 移除非判别性词后，若剩余 ≥ 3 个关键词 → 返回收紧后的新卡（immutable）
- 若移除后不足 3 个 → 放弃收紧，原卡保留（记录 WARN）

**GuardResult 字段：**

| 字段 | 含义 |
|------|------|
| `refined_cards` | 收紧后的候选卡列表（直接用于后续写入） |
| `at_risk_cases` | `{case_id: [新注入的 card_id]}` |
| `tightened_card_ids` | 被收紧关键词的卡 ID 列表 |
| `blocked_card_ids` | 被完全阻止写入的卡 ID（当前实现中为空，保留扩展空间） |

---

## Step 5：人工审核（interactive 模式）

仅在 `--mode interactive` 时执行。

逐张展示候选卡（title、when_to_use、keywords、tags、source_cases、experience、common_failure_prevented），用户逐一输入：
- `a` / 回车 → 批准
- `s` → 跳过
- `q` → 退出（已批准的仍继续执行）

---

## Step 6：写入卡片（`write_new_cards`）

**预处理：** 去除 Step 4 分配的临时 ID，让 `write_new_cards` 重新分配真实 ID（避免并发冲突）。

**写入前验证（`_validate_card_dict`）：**
- 必填字段：`title`、`when_to_use`、`experience`、`common_failure_prevented`
- 至少 3 个 `keywords`

**写入操作（顺序执行，immutable 模式）：**

1. 调用 `next_card_id(index)` 分配下一个 `exp-da-NNN`
2. `render_card_markdown()` 生成 Markdown 内容（包含 Experience / Checklist / Common failure prevented 三节）
3. `write_card_file()` 写入 `experience_cards/cards/{id}-{slug}.md`
4. `add_card_to_index()` 生成新 index dict（immutable，不修改原对象）
5. 循环结束后 `save_index()` 原子写入（write → rename）

**初始参数：**
- `confidence = 0.3`（`CONFIDENCE_GENERATED`）
- `priority = 3`（`confidence_to_priority(0.3)`）

---

## Step 6.5：检索验证（`validate_new_cards`）

**函数：** `validate_new_cards(new_card_ids, test_case_ids, cards_dir, instructions)`

重新加载刚写入的 index，对 `test_case_ids` 集合模拟检索，统计每张新卡被命中的 case 数量：

- 输出：`[card_id] X/Y test cases — OK`
- 0 命中 → 输出 `WARN: 0 retrieval hits on test cases`（此卡对测试集无效果）

---

## Step 7：运行 DA-Agent（`run_agent_on_cases`）

**调用命令：**
```bash
python run_parallel.py \
  --model deepseek-v3.2 \
  -s evolve_iter{N} \
  --example_index {0-based indices} \
  --use_experience \
  --max_steps 80 \
  -w 4
```

`--use_experience` 让 agent 在每次推理时从 `experience_cards/index.json` 检索相关卡并注入 prompt。

**结果导出：**
```bash
python get_results.py deepseek-v3.2-evolve_iter{N} \
  --output_dir evaluation_suite/agent_results/
```

输出目录：`evaluation_suite/agent_results/deepseek-v3.2-evolve_iter{N}/`

---

## Step 8：LLM Judge 评分（`run_llm_judge`）

**调用命令：**
```bash
python llm_judge.py \
  --rubrics-model deepseek-v3.2 \
  --gsb-model-text deepseek-v3.2 \
  --gsb-model-vis deepseek-v3.2 \
  --inputs evaluation_suite/agent_results/deepseek-v3.2-evolve_iter{N} \
  --max-workers 4
```

**评分维度：**
- Rubrics（3 项）：Completeness、Accuracy、Conclusiveness
- GSB（3 项）：Readability、Professionalism、Visualization

**输出：** `evaluation_suite/model_scores/deepseek-v3.2-evolve_iter{N}__*.csv`

---

## Step 9：比较得分 + 更新状态

### 9a. 比较得分（`compare_scores`）

```python
delta = new_weighted_total_score - baseline_weighted_total_score   # per case
avg_delta = mean(all deltas)
avg_delta_frac = avg_delta / 100.0
```

**注意：** `baseline_csv` 始终固定为原始 baseline，不随 multi-iteration 而改变。

### 9b. 更新置信度（`update_confidence`）

对本轮每张新卡，根据 `avg_delta_frac` 更新置信度：

| 条件 | 操作 |
|------|------|
| `avg_delta_frac > +0.02`（+2pp） | `confidence += 0.2`（上限 1.0） |
| `avg_delta_frac < -0.02`（-2pp） | `confidence -= 0.3`（下限 0.0） |
| 否则 | 不变 |

置信度对应的检索优先级：

| confidence | priority | 效果 |
|-----------|---------|------|
| ≥ 0.8 | 5 | 强优先检索 |
| ≥ 0.5 | 4 | 正常检索 |
| ≥ 0.2 | 3 | 正常检索（新卡默认） |
| < 0.2 | **0** | **禁止检索（disabled）** |

### 9c. 更新 Stagnation 状态（`update_case_state` + `mark_stagnant_cases`）

对每个测试 case：

1. 记录新得分到 `scores` 历史列表
2. 若 `new_score - prev_score >= 1.0pp` → `stagnation_count = 0`（改善）
3. 否则 → `stagnation_count += 1`
4. 同时记录 `failure_type`（本轮分类结果）

`mark_stagnant_cases(threshold=3)`：`stagnation_count ≥ 3` → `status = 'hard'`，下一轮 Step 1 将排除。

State 原子写入 `case_state.json`（write → rename）。

---

## Step 10：两层 Rollback 机制

### Step 10a：Surgical Rollback（`find_culprit_cards`）

**触发条件（per case）：**
- `baseline_weighted_total_score > 60`（高分 case，值得保护）
- `delta < -15pp`（本轮严重回退）

**定位罪魁：**
- 对每个触发 case，在**仅含新卡**的卡集合上模拟检索
- 被检索到的新卡 ID 加入 `culprit_ids`

**操作：**
```python
rollback_specific_cards(culprit_ids, index, cards_dir)
```
只删除 culprit 卡，**保留**对其他 case 有效的非 culprit 新卡。

---

### Step 10b：Avg-Delta Rollback（兜底）

**触发条件：** `avg_delta_frac < -0.02`（所有测试 case 平均 weighted delta < -2pp）

**操作：** 删除本轮剩余所有新卡（含非 culprit 卡）。

若 10a 已删除一些卡后 avg 仍 < -2pp，则 10b 继续删除剩余卡，保证整体不退步。

---

## Multi-Iteration 链式传递（auto 模式）

`--mode auto --max-iterations N` 时，`main()` 执行多轮循环，每轮调用 `run_pipeline()`：

```python
prev_result = None
for i in range(1, max_iterations + 1):
    traj_override = prev_result[0] if prev_result else None   # 上轮 agent 输出目录
    csv_override  = prev_result[1] if prev_result else None   # 上轮评分 CSV
    prev_result = run_pipeline(args, traj_override, csv_override)

    # 归档本轮 patterns，避免下轮重复提取
    patterns_dir.rename(f"patterns_iter{i}")
    patterns_dir.mkdir()
```

**两个 CSV 的区别：**

| CSV | 用途 | 是否随轮变化 |
|-----|------|-------------|
| `baseline_csv` | delta 对比基准（guard 阈值、rollback 判断） | **固定不变** |
| `extract_csv` | pattern 提取时的 rubrics row | 首轮用 baseline，后续轮用上轮输出 |

**链式效果：** 第 N+1 轮从第 N 轮 agent 输出中提取 pattern，看到的是**注入上轮 cards 后的残余失败**，避免重复提取相同 pattern。

---

## 检索评分算法（`retrieval.py`）

检索是**纯字符串匹配**，完全确定性，无向量/嵌入。对每张卡计算一个分数：

```
score = 关键词得分 + 组合奖励 + 标签得分 + 语义重叠
```

**各组件：**

| 组件 | 计算方式 | 分值 |
|------|----------|------|
| 多词关键词命中 | 关键词作为 token 短语完整出现在任务文本中 | +2.0 |
| 单词关键词命中 | 单 token 出现在任务 token 集合中 | +1.0 |
| 组合奖励 | ≥ 3 个关键词命中 且 ≥ 1 个标签命中 | +2.0 |
| 标签命中 | tag token 出现在任务 token 集合中 | +0.5 / tag |
| 语义重叠 | `(when_to_use + title)` 与任务文本的 token 重叠比 × 3.0，上限 1.5 | 0 ~ 1.5 |

**过滤规则（依次应用）：**
1. `priority == 0` → 直接跳过（disabled 卡）
2. `score < 3.0` → 过滤（绝对阈值）
3. `score < best_score × 0.5` → 过滤（相对阈值）
4. 最多返回 top-k = 4 张

**两个公共函数：**

```python
# 对全量 tasks 模拟检索，100 cases < 1s
simulate_retrieval_map(cards, tasks, top_k=4)
  → {case_id: [retrieved_card_id, ...]}

# 验证新卡能否被目标 cases 检索到
validate_new_cards(new_card_ids, test_case_ids, cards_dir, instructions)
  → {card_id: [hit_case_ids]}
```

---

## 关键常量汇总

| 常量 | 值 | 含义 |
|------|----|------|
| `MIN_RETRIEVAL_SCORE` | 3.0 | 最低检索分（绝对阈值） |
| `DEFAULT_TOP_K` | 4 | 每次最多检索卡数 |
| `HIGH_BASELINE_THRESHOLD` | 60.0 | Surgical rollback 触发的 baseline 分 |
| `CASE_REGRESSION_THRESHOLD` | -15.0 | Surgical rollback 触发的 per-case delta |
| `IMPROVEMENT_THRESHOLD` | 0.02 | 置信度提升触发的 avg delta（fractions） |
| `REGRESSION_THRESHOLD` | -0.02 | 全量 rollback 触发的 avg delta（fractions） |
| `CONFIDENCE_GENERATED` | 0.3 | 新卡初始置信度 |
| `stagnation_threshold` | 3 | 连续多少轮无改善 → 标记为 hard |

---

## CLI 参数速查

```bash
python evolve_pipeline.py \
  --mode        interactive|auto|dry-run  \
  --n-cases     10          # 提取 pattern 的 case 数量
  --test-n      5           # 跑 agent + 评分的 case 数量
  --iteration   1           # 用于命名输出目录
  --max-iterations 3        # auto 模式最大轮数
  --baseline-csv <path>     # 固定基准 CSV
  --traj-dir    <path>      # agent 轨迹目录
  --cards-dir   <path>      # experience_cards 目录
  --patterns-dir <path>     # patterns 缓存目录
  --case-file   <path>      # 指定 case 列表（跳过自动排序）
  --max-workers 4           # agent + judge 并发数
  --skip-agent-run          # 只写卡不跑 agent（快速验证）
  --force-extract           # 强制重提取（忽略已有缓存）
  --use-contrast            # 启用对比学习
```
