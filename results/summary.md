# 结果汇总

> 所有数字来自 `results/samples/` 与原始运行日志。评分为宽松匹配，非官方脚本。

## 1. AIME24（前 10 题，四种配置）

| 配置 | planner | 其余角色 | 准确率 |
|---|---|---|---|
| A | Qwen2.5-7B | Qwen2.5-7B | 0/10 |
| B | AgentFlow-7B | AgentFlow-7B | 0/10 |
| C1 | AgentFlow-7B | qwen-plus | 6/10 |
| D1 | Qwen2.5-7B | qwen-plus | 5/10 |

## 2. 多跳（各 10 题）

| 数据集 | C2（作者 planner） | D2（Qwen planner） |
|---|---|---|
| HotpotQA | 4/10 | 4/10 |
| Musique | 3/10 | 2/10 |
| 2Wiki | 6/10 | 5/10 |
| **合计** | **13/30** | **11/30** |

## 3. B 组（无搜索基准）

| 数据集 | E（作者 planner） | F（Qwen planner） |
|---|---|---|
| AIME24（20） | 8/20 | 8/20 |
| AMC23（10） | 8/10 | 7/10 |
| GPQA（10） | 7/10 | 7/10 |
| MedQA（10） | 10/10 | 10/10 |
| GameOf24（10） | 8/9 | 9/10 |
| **合计** | **41/59** | **41/60** |

## 4. 机制观测

| 观测 | 数值 |
|---|---|
| Planner 单轮 prompt 长度 | 7,272 字符（题目仅 110） |
| 工具说明书占比 | 56% |
| 历史增长 | 5,584 → 6,038 → 6,813 字符（第 1/2/3 轮） |
| 多跳工具调用总数 | 86 次 |
| 其中 `relevant_pages` 非空 | **0 次** |
| Verifier 误判案例 | `"I would not stop here"` → STOP |

## 5. 复现环境

- GPU：RTX 4090D 24G
- vLLM：0.11.0，`--dtype bfloat16`，`--max-model-len 16384`
- planner：`AgentFlow/agentflow-planner-7b`（fp32→bf16）
- executor / verifier / planner_fixed：DashScope `qwen-plus`
- 工具模型：OpenAI `gpt-4o-mini`
