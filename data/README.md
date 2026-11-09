# 数据集说明

本仓库**不包含**任何 benchmark 数据文件，请从原始发布处获取，并遵循各自许可。

| 数据集 | 题量 | 来源 | 许可 |
|---|---|---|---|
| AIME24 | 30 | https://huggingface.co/datasets/AI-MO/aimo-validation-aime | 见发布页 |
| AMC23 | 40 | https://huggingface.co/datasets/AI-MO/aimo-validation-amc | 见发布页 |
| GameOf24 | 300 | https://huggingface.co/datasets/JoPmt/GameOf24 | 见发布页 |
| MedQA | 300 | https://github.com/jind11/MedQA | 见仓库 |
| GPQA | 300 | https://github.com/idavidrein/gpqa | 见仓库 |
| GAIA | 127 | https://huggingface.co/datasets/gaia-benchmark/GAIA | 见发布页 |
| HotpotQA | 100 | https://hotpotqa.github.io/ | CC BY-SA 4.0 |
| Musique | 200 | https://github.com/StonyBrookNLP/musique | CC BY 4.0 |
| 2WikiMultiHopQA | 200 | https://github.com/Alab-NII/2wikimultihop | MIT |
| Bamboogle | 125 | https://huggingface.co/datasets/chiayewken/bamboogle | 见发布页 |

## 格式约定

脚本期望每个数据集是一个 JSON 数组，元素至少包含：

```json
{
  "query": "题目文本",
  "answer": "标准答案",
  "image": null
}
```

`gameof24` 的 `answer` 是表达式列表，`gpqa` 额外有 `choices` / `answer_idx`，`medqa` 有 `options`。

## 我们实际使用的子集

- AIME24：20 题（索引 0–19）
- AMC23 / GPQA / MedQA / GameOf24：各 10 题（索引 0–9）
- HotpotQA / Musique / 2Wiki：各 10 题（索引 0–9）

样本量小，结论只作机制分析，不作性能排名。
