"""Score the B-group benchmarks (numeric / MCQ / expression).

Usage:
    python score_math2.py [model] [runs_dir]

Defaults: model = agentflow-planner-7b, runs_dir = <repo>/results/runs
"""

import json
import os
import re
import string
import sys

REPRO_ROOT = os.environ.get("REPRO_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AF_ROOT = os.environ.get("AF_ROOT", os.path.expanduser("~/AgentFlow"))
MODEL = sys.argv[1] if len(sys.argv) > 1 else "agentflow-planner-7b"
RUNS = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPRO_ROOT, "results", "runs")

SPECS = [
    ("aime24", 20, "num"),
    ("amc23", 10, "num"),
    ("gpqa", 10, "mcq_idx"),
    ("medqa", 10, "mcq_text"),
    ("gameof24", 10, "expr"),
]


def norm(s):
    s = str(s).lower().strip().replace("\u2019", "'")
    s = s.translate(str.maketrans("", "", string.punctuation))
    return " ".join(s.split())


def extract(text):
    m = re.findall(r"<answer>(.*?)</answer>", str(text), re.DOTALL)
    return m[-1].strip() if m else str(text).strip()


def last_num(s):
    nums = re.findall(r"-?\d+", str(s).replace(",", ""))
    return nums[-1] if nums else None


def eval24(expr, nums):
    e = str(expr).split("=")[0]
    e = e.replace("×", "*").replace("÷", "/").replace("−", "-").replace("·", "*")
    e = re.sub(r"[^0-9+\-*/(). ]", "", e)
    if not e.strip():
        return False
    try:
        v = eval(e, {"__builtins__": {}}, {})
    except Exception:
        return False
    used = sorted(int(x) for x in re.findall(r"\d+", e))
    return used == sorted(nums) and abs(v - 24) < 1e-6


total_ok = total_n = 0
for ds, n, kind in SPECS:
    data = json.load(open(os.path.join(AF_ROOT, "test", ds, "data", "data.json"), encoding="utf-8"))
    ok = cnt = 0
    misses = []
    for i in range(min(n, len(data))):
        f = os.path.join(RUNS, f"{ds}_{MODEL}_{i}.json")
        if not os.path.exists(f):
            continue
        out = json.load(open(f, encoding="utf-8"))
        pred = extract(str(out.get("direct_output", "")))
        cnt += 1
        hit = False
        if kind == "num":
            gt = last_num(data[i].get("answer"))
            hit = gt is not None and last_num(pred) == gt
        elif kind == "mcq_idx":
            gt = "ABCD"[int(data[i]["answer_idx"])]
            m = re.search(r"\b([A-D])\b", pred)
            hit = bool(m) and m.group(1) == gt
        elif kind == "mcq_text":
            gt = norm(data[i].get("answer"))
            m = re.search(r"\b([A-D])\b", pred)
            if m:
                idx = "ABCD".index(m.group(1))
                opts = data[i].get("options") or []
                cand = norm(opts[idx]) if idx < len(opts) else ""
                hit = gt in cand or cand in gt or gt in norm(pred)
            else:
                hit = gt in norm(pred)
        elif kind == "expr":
            nums = [int(x) for x in re.findall(r"\d+", str(data[i].get("question")))]
            hit = eval24(pred, nums)
        ok += hit
        if not hit and len(misses) < 2:
            misses.append((i, str(data[i].get("answer"))[:36], pred[:36]))
    print(f"{ds:10} {ok}/{cnt}")
    for m in misses:
        print(f"    miss {m[0]}: gt={m[1]!r} pred={m[2]!r}")
    total_ok += ok
    total_n += cnt

print(f"TOTAL      {total_ok}/{total_n}")
