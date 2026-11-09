# Planner 第一轮真实 Prompt（原文 + 注释）

> 来源：租用机实测，`smoke_real.json` 的 `action_predictor_1_prompt` 字段。
> 模型：Qwen2.5-7B-Instruct（vLLM），题目：书店卖书。
> 总长度 **7272 字符 / 56 行**。

## 0. 先看构成：题目只占 1.5%

| 段落 | 字符数 | 占比 | 每轮变不变 |
|---|---:|---:|---|
| 任务说明 | 110 | 2% | 不变 |
| **题目 Query** | **110** | **2%** | 不变 |
| 审题 Query Analysis | 1916 | 26% | 不变 |
| 工具名单 | 68 | 1% | 不变 |
| **工具说明书 Metadata** | **4090** | **56%** | 不变（每轮重复） |
| 历史 Previous Steps | 2 | 0% | **每轮变长** |
| 指令/格式/规则 | 843 | 12% | 不变 |

**一句话**：7,272 字符里，真正属于"这道题"的只有 110 字符；其余 98% 是模板、说明书和格式要求。

---

## 1. 任务说明

```text
Task: Determine the optimal next step to address the query using available tools and previous steps.

Context:
```

---

## 2. 题目（110 字符）

```text
A bookstore had 48 copies. It sold 3/8 on Monday and 12 on Tuesday. How many are left? Answer with the number.
```

---

## 3. 审题结果（1916 字符，由 fixed 模型一次性生成）

```text
### Summary of the Query
The query asks how many copies of a bookstore's inventory are left after selling some books on Monday and Tuesday. The initial stock was 48 copies, 3/8 were sold on Monday, and 12 were sold on Tuesday.

### Necessary Skills and Tools
#### Skills:
1. **Arithmetic Operations**: Basic addition, subtraction, multiplication, and division.
2. **Problem-Solving**: Breaking down the problem into smaller steps.

#### Tools:
1. **Generalist_Solution_Generator_Tool**
2. **Python_Code_Generator_Tool**

### Explanations

**Skills:**
- **Arithmetic Operations**: Essential for performing calculations such as finding fractions of numbers (3/8) and subtracting quantities.
- **Problem-Solving**: Required to decompose the problem into manageable parts (e.g., calculating sales for Monday separately from Tuesday).

**Tools:**
- **Generalist_Solution_Generator_Tool**: Useful for step-by-step reasoning if basic arithmetic isn't sufficient or if more complex logic is needed beyond simple operations.
- **Python_Code_Generator_Tool**: Ideal for automating arithmetic calculations quickly using code snippets tailored to solve the specific problem at hand.

### Additional Considerations
- Since this query deals with straightforward arithmetic operations that involve no external dependencies or complex algorithms, both tools can be used effectively.
- If choosing between these tools based solely on simplicity and effectiveness:
    - Use `Python_Code_Generator_Tool` directly due to its focus on basic math problems requiring minimal setup.
    - Use `Generalist_Solution_Generator_Tool` as a fallback or secondary method if Python’s capabilities aren’t immediately apparent but might help clarify steps through detailed explanation.

By leveraging these skills and tools appropriately, one can efficiently determine how many book copies remain in stock following the specified sales transactions.
```

> 注意：这是"辅助脑"（未训练的 instruct 模型）写的，之后每轮原样重复贴给"决策脑"。

---

## 4. 工具名单（68 字符）

```text
['Generalist_Solution_Generator_Tool', 'Python_Code_Generator_Tool']
```

这就是 Planner 能选的**全部动作**（action 空间）。

---

## 5. 工具说明书（4090 字符，占全文 56%）

这是 `Initializer` 从每个工具实例上抓下来的 metadata，**4 个工具全部列出，每轮重复**：

```text
{'Generalist_Solution_Generator_Tool': {'tool_name': 'Generalist_Solution_Generator_Tool', 'tool_description': 'A generalized tool that takes query from the user, and answers the question step by step to the best of its ability. It can also accept an image.', 'tool_version': '1.0.0', 'input_types': {'query': 'str - The query that includes query from the user to guide the agent to generate response.'}, 'output_type': 'str - The generated response to the original query', 'demo_commands': [{'command': 'execution = tool.execute(query="Summarize the following text in a few lines")', 'description': 'Generate a short summary given the query from the user.'}], 'user_metadata': {'limitation': '\nThe Generalist_Solution_Generator_Tool may provide hallucinated or incorrect responses.\n', 'best_practice': "\nFor optimal results with the Generalist_Solution_Generator_Tool:\n1. Use it for general queries or tasks that don't require specialized knowledge or specific tools in the toolbox.\n2. Provide clear, specific query.   \n3. Use it to answer the original query through step by step reasoning for tasks without complex or multi-step reasoning.\n4. For complex queries, break them down into subtasks and use the tool multiple times.\n5. Use it as a starting point for complex tasks, then refine with specialized tools.\n6. Verify important information from its responses.\n"}, 'require_llm_engine': True}, 'Python_Code_Generator_Tool': {'tool_name': 'Python_Code_Generator_Tool', 'tool_description': 'A tool that generates and executes simple Python code snippets for basic arithmetical calculations and math-related problems. The generated code runs in a highly restricted environment with only basic mathematical operations available.', 'tool_version': '1.0.0', 'input_types': {'query': 'str - A clear, specific description of the arithmetic calculation or math problem to be solved, including any necessary numerical inputs.'}, 'output_type': 'dict - A dictionary containing the generated code, calculation result, and any error messages.', 'demo_commands': [{'command': 'execution = tool.execute(query="Find the sum of prime numbers up to 50")', 'description': 'Generate a Python code snippet to find the sum of prime numbers up to 50.'}, {'command': 'query="Given the list [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], calculate the sum of squares of odd numbers"\nexecution = tool.execute(query=query)', 'description': 'Generate a Python function for a specific mathematical operation on a given list of numbers.'}], 'user_metadata': {'limitations': "\nThe Python_Code_Generator_Tool has several limitations:\n1. Restricted to basic Python arithmetic operations and built-in mathematical functions.\n2. Cannot use any external libraries or modules, including those in the Python standard library.\n3. Limited to simple mathematical calculations and problems.\n4. Cannot perform any string processing, data structure manipulation, or complex algorithms.\n5. No access to any system resources, file operations, or network requests.\n6. Cannot use 'import' statements.\n7. All calculations must be self-contained within a single function or script.\n8. Input must be provided directly in the query string.\n9. Output is limited to numerical results or simple lists/tuples of numbers.\n10. Output should be kept to a single numerical result or a simple list/tuple of numbers.\n11. DO NOT generate loop output.\n", 'best_practices': '\nFor optimal results with the Python_Code_Generator_Tool:\n1. Provide clear and specific queries that describe the desired mathematical calculation.\n2. Include all necessary numerical inputs directly in the query string.\n3. Keep tasks focused on basic arithmetic, algebraic calculations, or simple mathematical algorithms.\n4. Ensure all required numerical data is included in the query.\n5. Verify that the query only involves mathematical operations and does not require any data processing or complex algorithms.\n6. Review generated code to ensure it only uses basic Python arithmetic operations and built-in math functions.\n'}, 'require_llm_engine': True}}
```

> 观察：里面 `demo_commands`、`limitation`、`best_practice` 都是给"写代码"用的说明，对"选哪个工具"其实帮助有限，但每轮都要占 ~4,000 字符。

---

## 6. 历史（第一轮是空的）

```text
{}
```

第二轮开始，这里会变成：

```text
{'Action Step 1': {'tool_name': 'Python_Code_Generator_Tool',
  'sub_goal': '...', 'command': 'execution = tool.execute(...)',
  'result': [{'printed_output': 'Number of books left: 18.0', ...}]}}
```

---

## 7. 指令 / 输出格式 / 规则（843 字符）

```text
Instructions:
1. Analyze the query, previous steps, and available tools.
2. Select the **single best tool** for the next step.
3. Formulate a specific, achievable **sub-goal** for that tool.
4. Provide all necessary **context** (data, file names, variables) for the tool to function.

Response Format:
1.  **Justification:** Explain your choice of tool and sub-goal.
2.  **Context:** Provide all necessary information for the tool.
3.  **Sub-Goal:** State the specific objective for the tool.
4.  **Tool Name:** State the exact name of the selected tool.

Rules:
- Select only ONE tool.
- The sub-goal must be directly achievable by the selected tool.
- The Context section must contain all information the tool needs to function.
- The response must end with the Context, Sub-Goal, and Tool Name sections in that order, with no extra content.
```

---

## 8. 从这份原文能直接看出的四件事

1. **动作空间是显式枚举的**：`Available Tools` 那行就是全部可选值；
2. **信息严重冗余**：6006 字符（83%）是"每轮不变"的背景材料，却每轮都重发；
3. **真正的任务信息极少**：题目 110 字符，其余靠模型自己从审题结果里找方向；
4. **历史是 Python dict 的 repr**（不是 JSON），带单引号、`None` 之类，模型要自己"读懂"这种格式。

---

## 9. 与输出的关系

模型看到这 7,272 字符后，被要求输出：

```text
Justification: ...
Context: ...
Sub-Goal: ...
Tool Name: ...
```

而实际输出（同一轮）：

```text
**Justification:** The problem involves basic arithmetic operations...
**Context:** - Initial number of book copies: 48 ...
**Sub-Goal:** Calculate the remaining number of book copies...
**Tool Name:** Python_Code_Generator_Tool
```

`json.loads` 失败 → 正则解析 → 得到三元组。这就是"Planner 的输出形式"。
