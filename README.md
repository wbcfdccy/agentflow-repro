# AgentFlow 复现：四模块机制剖析与评测（非官方）

> 对论文 **In-the-Flow Agentic System Optimization for Effective Planning and Tool Use**（ICLR 2026）的独立复现。
> **只做推理与评测，不做训练**：planner 使用作者发布的 `AgentFlow/agentflow-planner-7b` 权重，全程冻结。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 这个仓库是什么

它不是一个"刷榜"仓库，而是一份**机制剖析 + 小规模评测**的复现记录。目标是回答四个具体问题：

1. **Planner 的输入是什么？输出是什么形式？**
2. **Planner 的结果是怎么进入 Executor 的？是 plan 还是 prompt？**
3. **Verifier 每轮输出什么？可信吗？它的内容如何影响下一轮？**
4. **Action（工具）的取值范围是什么？不同数据集会变吗？**

我们做的是：用官方代码 + 作者权重 + 真实工具（Wikipedia / Python / Generalist），把每一步的 prompt、模型原始输出、解析结果、记忆内容全部落盘，逐题对照。

**我们没做**：Flow-GRPO 训练、全量 benchmark、官方评分脚本、Google 搜索（缺 Gemini key）。

---

## 关键发现

1. **Planner 的输入 98% 与题目无关**
   实测一轮 prompt 共 7,272 字符，其中题目仅 110 字符（2%），工具说明书 4,090 字符（56%），审题结果 1,916 字符（26%）。工具说明每轮重复发送。

2. **"Plan" 并不存在，传下去的是三元组**
   `(context, sub_goal, tool_name)` 三个字符串被拼进 Executor 的新 prompt，由另一个模型写出一行
   `execution = tool.execute(query="...")`，再由 Python `exec` 执行。`justification` 在解析时被丢弃。

3. **Verifier 是"停止开关"，不是"验证器"**
   它只输出 `STOP / CONTINUE`，只影响 `break`；它的 analysis 不写回 memory，下一轮 Planner 完全看不到。解析走"正则 → 子串兜底"：文本里出现 `stop` 就可能被判 STOP（`"I would not stop here"` 也会）。

4. **决定成败的是 Executor，不是 Planner**
   同一套 harness 下：全 Qwen 底座 0/10、全作者权重 0/10；把 executor 换成能干活的模型后跳到 5–6/10。作者 planner 相对底座 planner 的差异在 1–2 题内，样本量下不显著。

5. **Wikipedia 工具在我们的环境中"只搜不读"**
   86 次工具调用中 `relevant_pages` 全部为空——"选相关页面"依赖结构化输出，而 vLLM/DashScope 忽略 `response_format`，解析失败后返回空列表。多跳成绩因此主要反映模型的参数记忆，而非检索能力。

---

## 实验结果

### 配置说明

| 组 | planner | executor / verifier / planner_fixed | 工具 | 数据集（题数） |
|---|---|---|---|---|
| A | Qwen2.5-7B | Qwen2.5-7B | DashScope | AIME24（10） |
| B | AgentFlow-7B | AgentFlow-7B | DashScope | AIME24（10） |
| C1 | AgentFlow-7B | qwen-plus | DashScope | AIME24（10） |
| D1 | Qwen2.5-7B | qwen-plus | DashScope | AIME24（10） |
| C2 | AgentFlow-7B | qwen-plus | gpt-4o-mini + Wikipedia | HotpotQA / Musique / 2Wiki（各 10） |
| D2 | Qwen2.5-7B | qwen-plus | gpt-4o-mini + Wikipedia | HotpotQA / Musique / 2Wiki（各 10） |
| E | AgentFlow-7B | qwen-plus | gpt-4o-mini | AIME24(20) / AMC23(10) / GPQA(10) / MedQA(10) / GameOf24(10) |
| F | Qwen2.5-7B | qwen-plus | gpt-4o-mini | 同上 |

### 结果

| 配置 | AIME24（10 题） |
|---|---|
| A 全底座 | 0/10 |
| B 全作者 | 0/10 |
| C1 作者 planner + qwen-plus | **6/10** |
| D1 Qwen planner + qwen-plus | 5/10 |

| 数据集 | C2（作者 planner） | D2（Qwen planner） |
|---|---|---|
| HotpotQA | 4/10 | 4/10 |
| Musique | 3/10 | 2/10 |
| 2Wiki | 6/10 | 5/10 |
| 合计 | 13/30 | 11/30 |

| 数据集 | E（作者 planner） | F（Qwen planner） |
|---|---|---|
| AIME24 | 8/20 | 8/20 |
| AMC23 | 8/10 | 7/10 |
| GPQA | 7/10 | 7/10 |
| MedQA | 10/10 | 10/10 |
| GameOf24 | 8/9 | 9/10 |
| 合计 | **41/59** | **41/60** |

> 评分为宽松匹配（`<answer>` 归一化包含 / 字母选项），非官方脚本，存在高估与低估。

---

## 复现步骤

### 0. 前置

- 一张 ≥24GB 显存的 GPU（7B bf16 约 15GB）
- Python 3.10+，`vllm==0.11.0`（或任何支持 Qwen2 的版本）
- DashScope API Key（executor / verifier / planner_fixed）
- 可选：OpenAI API Key（官方工具模型 `gpt-4o-mini`、Wikipedia RAG）

### 1. 准备代码与模型

```bash
git clone https://github.com/lupantech/AgentFlow.git
cd AgentFlow

# 本仓库的 runner 依赖这个软链（原仓库的包布局是 agentflow/agentflow）
mkdir -p lib
ln -s "$(pwd)/agentflow/agentflow" lib/agentflow
# Windows: New-Item -ItemType Junction -Path lib\agentflow -Target agentflow\agentflow

# 作者权重（约 30GB，fp32）
huggingface-cli download AgentFlow/agentflow-planner-7b --local-dir ./models/planner-7b
# 可选：转 bf16 省一半空间（见 docs/01 附录）
```

### 2. 起 vLLM

```bash
python -m vllm.entrypoints.openai.api_server \
  --model ./models/planner-7b \
  --served-model-name agentflow-planner-7b \
  --port 8000 --max-model-len 16384 --dtype bfloat16 \
  --gpu-memory-utilization 0.85
```

### 3. 配置环境变量

```bash
export AF_ROOT=/path/to/AgentFlow      # runner 用它定位代码与 test/ 数据
export DASHSCOPE_API_KEY=sk-...
export OPENAI_API_KEY=sk-...           # 可选；走本地代理时另设 HTTPS_PROXY
```

> 本仓库的 `scripts/run_real.py` 通过 `AF_*` 环境变量或命令行参数指定引擎与端点，不会硬编码任何密钥。

### 4. 跑评测

```bash
# 单题（会打印每步 Planner/Executor/Verifier 的输入输出）
python scripts/run_real.py --data test/aime24/data/data.json --index 0 \
  --model agentflow-planner-7b --max_steps 6 --output_types direct --out run.json

# 批量并发（B 组）
bash scripts/bench_math2.sh agentflow-planner-7b 6 20 10

# 多跳（需要 Wikipedia 工具与 OpenAI key）
bash scripts/bench_multi.sh agentflow-planner-7b 3 9

# 评分
python scripts/score_math2.py agentflow-planner-7b
python scripts/score_multi.py agentflow-planner-7b
```

> 注：官方 `test/solve.py` 在本仓库的目录结构下 `agentflow.agentflow.*` 导入不成立，`run_real.py` 做了等价的组件装配（并绕过了 `vllm` 包导入），不改动原仓库任何代码。

### 5. 生成分析文档

```bash
python scripts/gen_module_io.py     # 逐题四模块 I/O
python scripts/gen_multi_detail.py  # 多跳逐题对照
```

---

## 目录结构

```
docs/                       分析文档
  01-四问回答.md            四个问题的完整回答（含实验证据）
  02-代码导读.md            Planner/Executor/Verifier/Generator 源码逐段讲解
  03-模块输入输出实录.md    实测的 prompt / 输出 / 记忆
  04-多跳逐题明细.md        30 道多跳题逐题对照
  05-论文评价.md            对论文创新点的评价
  prompts/                  Planner 真实 prompt 原文
scripts/                    复现脚本（runner、批跑、评分、文档生成）
results/                    汇总结果与样例 trace
data/                       数据集说明（不包含数据本体）
```

---

## 局限

- 未训练，仅评测作者权重；
- 单卡 24G，用 `qwen-plus` 代替官方 `qwen2.5-7b-instruct`（后者在我们的 DashScope 工作空间无权限）；
- 缺 Google 搜索，多跳只用 Wikipedia，且 Wikipedia 检索在本环境失效；
- 样本 10–20 题；
- 评分器为宽松匹配；
- OpenAI 依赖本机反向隧道，稳定性受限。

---

## 伦理与合规

- 本仓库**不包含**任何模型权重、API Key、服务器凭据或论文原文；
- `docs/` 中引用的 benchmark 题目版权归原数据集所有（HotpotQA / Musique / 2WikiMultiHopQA），仅用于分析说明，请遵循各自许可；
- 仓库代码基于 [AgentFlow](https://github.com/lupantech/AgentFlow)（MIT），见 `NOTICE`。

---

## 引用

```bibtex
@inproceedings{li2026agentflow,
  title     = {In-the-Flow Agentic System Optimization for Effective Planning and Tool Use},
  author    = {Li, Zhuofeng and Zhang, Haoxiang and Han, Seungju and Liu, Sheng and Xie, Jianwen
               and Zhang, Yu and Choi, Yejin and Zou, James and Lu, Pan},
  booktitle = {ICLR},
  year      = {2026}
}
```

## License

MIT，见 [LICENSE](LICENSE)。
