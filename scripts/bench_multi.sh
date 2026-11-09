#!/bin/bash
# Multi-hop benchmarks with the Wikipedia tool, concurrent.
#   bash bench_multi.sh [model] [concurrency] [last_index]
#
# Requires OPENAI_API_KEY (the Wikipedia tool uses it for RAG) and working
# network access to en.wikipedia.org.
set -u

REPRO_ROOT=${REPRO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
AF_ROOT=${AF_ROOT:-$HOME/AgentFlow}
PYTHON=${PYTHON:-python}
MODEL=${1:-agentflow-planner-7b}
CONC=${2:-3}
LAST=${3:-9}

TOOLS="Base_Generator_Tool,Python_Coder_Tool,Wikipedia_Search_Tool"
ENGINES=${AF_TOOL_ENGINES:-gpt-4o-mini,gpt-4o-mini,gpt-4o-mini}

export REPRO_ROOT AF_ROOT PYTHON MODEL CONC TOOLS ENGINES
mkdir -p "$REPRO_ROOT/results/runs"

for ds in hotpotqa musique 2wiki; do
  echo "=========== $ds (0..$LAST) ==========="
  export ds
  seq 0 "$LAST" | xargs -P "$CONC" -I{} bash -c '
    timeout 1800 "$PYTHON" "$REPRO_ROOT/scripts/run_real.py" \
      --data "test/$ds/data/data.json" --index {} --max_steps 6 --model "$MODEL" \
      --tools "$TOOLS" --tool_engines "$ENGINES" \
      --output_types direct --out "$REPRO_ROOT/results/runs/${ds}_${MODEL}_{}.json" \
      > "$REPRO_ROOT/results/runs/${ds}_${MODEL}_{}.log" 2>&1
    echo "  done $ds {} $(date +%H:%M:%S)"
  '
done
echo "MULTI_DONE $(date)"
