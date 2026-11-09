"""Score the multi-hop runs: normalized match of <answer> vs ground truth.

Usage:
    python score_multi.py [model] [runs_dir]
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
N = 10

DATASETS = {name: os.path.join(AF_ROOT, "test", name, "data", "data.json")
            for name in ("hotpotqa", "musique", "2wiki")}


def norm(s):
    s = str(s).lower().strip().replace("\u2019", "'")
    s = s.translate(str.maketrans("", "", string.punctuation))
    return " ".join(s.split())


def extract(text):
    m = re.findall(r"<answer>(.*?)</answer>", str(text), re.DOTALL)
    return m[-1].strip() if m else str(text).strip()


for ds, path in DATASETS.items():
    data = json.load(open(path, encoding="utf-8"))
    ok = total = 0
    misses = []
    for i in range(N):
        f = os.path.join(RUNS, f"{ds}_{MODEL}_{i}.json")
        if not os.path.exists(f):
            continue
        out = json.load(open(f, encoding="utf-8"))
        gt = data[i].get("answer", "")
        pred = extract(str(out.get("direct_output", "")))
        total += 1
        hit = norm(gt) in norm(pred) or norm(pred) == norm(gt)
        ok += hit
        if not hit and len(misses) < 3:
            misses.append((i, str(gt)[:40], pred[:40]))
    print(f"{ds:10} {ok}/{total}")
    for m in misses:
        print(f"    miss {m[0]}: gt={m[1]!r} pred={m[2]!r}")
