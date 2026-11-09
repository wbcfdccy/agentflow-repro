# Planner 第二轮 Prompt（带历史）——真实运行

> 来源：租用机实测 `continue_case.json`（题目：100th prime × 冰岛人口；只开 Python 工具）。
> 三轮全部真实调用，非模拟。

## 0. 三轮的长度变化

| 轮次 | Prompt 总字符 | 其中 Previous Steps | 增量 |
|---|---:|---:|---:|
| 第 1 轮 | 5584 | 2（空 `{}`） | — |
| 第 2 轮 | 6038 | 456 | +454 |
| 第 3 轮 | 6813 | 1231 | +775 |

**每一轮都在变长**，涨的全部是 `Previous Steps`。其余段落（题目、审题、工具说明、指令）完全不变。

---

## 1. 第二轮 Prompt 里最关键的那一段

除了下面这段，第二轮和第一轮**一字不差**：

```text
{'Action Step 1': {'tool_name': 'Python_Code_Generator_Tool', 'sub_goal': "Generate a Python script that finds the 100th prime number and allows us to input Iceland's population in 2025, then compute their product.\n\n4.", 'command': 'execution = tool.execute(query="Find the 100th prime number and multiply it by the population of Iceland in 2025 which is provided as a numerical value.")', 'result': [{'error': 'unexpected indent (<string>, line 24)'}]}}
```

拆开看，这是 Python dict 的 repr，四个键：

- `tool_name`：上一步用了什么工具
- `sub_goal`：上一步的子目标（注意结尾带了 `\n\n4.`，这是正则解析时把模型列表编号一起吞进来的）
- `command`：上一步真正执行的代码
- `result`：工具返回的结果（这次是 `{'error': 'unexpected indent ...'}`）

---

## 2. Planner 看到这条历史后的输出

```text
1. **Justification:** The `Python_Code_Generator_Tool` is the most suitable tool for this task because it can generate and execute Python code to find the 100th prime number and perform the required multiplication once we have Iceland's population in 2025.

2. **Context:** 
   - We need to find the 100th prime number.
   - Once we have that, we will multiply it by Iceland's population in 2025.
   - The population of Iceland in 2025 needs to be provided as a numerical value.

3. **Sub-Goal:**
   Generate a Python script that finds the 100th prime number and allows us to input Iceland's population in 2025, then compute their product.

4. **Tool Name:** Python_Code_Generator_Tool

**Context:**
- We need to provide a clear query for finding the 100th prime number and allowing input for Iceland's population in 2025.
- We will use numerical values when providing Icelandic population data.

**Sub-Goal:**
Generate a Python script that finds the first hundred primes using an efficient algorithm like Sieve of Eratosthenes, prompts for entering Iceland’s projected or actual population for year 'TBD', then calculates and outputs their product.

**Tool Name:** Python_Code_Generator_Tool
```

**它仍然选了 `Python_Code_Generator_Tool`。** 第三轮也一样。

---

## 3. 这一组数据说明了什么

1. **报错确实进了状态**：`result` 里明明白白写着 `unexpected indent`；
2. **但策略没有改变**：三轮都选同一个工具，因为未训练的模型不会把"上次报错"映射成"换一个工具"；
3. **解析有污染**：`sub_goal` 尾部粘了 `4.` 这种列表编号，说明正则把模型的排版当成了内容；
4. **Verifier 三轮都判 CONTINUE**，循环靠 `max_steps` 才停下——不是"收敛"，是"耗尽"。

这正好对应之前讨论的多轮 MDP：状态（memory）在变，动作（tool_name）不变，说明这个策略还没学会利用状态。

---

## 4. 对照：第一轮与第二轮的差异只有这一块

```text
第 1 轮 Previous Steps: {}
第 2 轮 Previous Steps: {'Action Step 1': {...}}
```

所以"Planner 每轮多知道了什么"，答案就是：**多知道了上一步用了什么工具、写了什么代码、返回了什么结果**。仅此而已——没有 Verifier 的意见，没有 Executor 的解释。
