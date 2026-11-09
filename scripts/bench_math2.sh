#!/bin/bash
# B group: no-search benchmarks (math / science / medical), concurrent.
#   bash bench_math2.sh [model] [concurrency] [aime_n] [other_n]
#
# Env:
#   AF_ROOT     AgentFlow checkout (default ~/AgentFlow)
#   REPRO_ROOT  this repository root (default: parent of this script)
#   PYTHON      python interpreter (default: python)
set -u

REPRO_ROOT=${REPRO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
AF_ROOT=${AF_ROOT:-$HOME/AgentFlow}
PYTHON=${PYTHON:-python}
MODEL=${1:-agentflow-planner-7b}
CONC=${2:-6}
AIME_N=${3:-20}
OTHER_N=${4:-10}

TOOLS="Base_Generator_Tool,Python_Coder_Tool"
ENGINES=${AF_TOOL_ENGINES:-gpt-4o-mini,gpt-4o-mini}

export REPRO_ROOT AF_ROOT PYTHON MODEL TOOLS ENGINES
mkdir -p "$REPRO_ROOT/results/runs"

run_ds() {
  local ds=$1 last=$2
  echo "=========== $ds (0..$last) ==========="
  export ds
  seq 0 "$last" | xargs -P "$CONC" -I{} bash -c '
    timeout 1800 "$PYTHON" "$REPRO_ROOT/scripts/run_real.py" \
      --data "test/$ds/data/data.json" --index {} --max_steps 6 --model "$MODEL" \
      --tools "$TOOLS" --tool_engines "$ENGINES" --force_format \
      --output_types direct --out "$REPRO_ROOT/results/runs/${ds}_${MODEL}_{}.json" \
      > "$REPRO_ROOT/results/runs/${ds}_${MODEL}_{}.log" 2>&1
    echo "  done $ds {} $(date +%H:%M:%S)"
  '
}

run_ds aime24 $((AIME_N - 1))
run_ds amc23 $((OTHER_N - 1))
run_ds gpqa $((OTHER_N - 1))
run_ds medqa $((OTHER_N - 1))
run_ds gameof24 $((OTHER_N - 1))
echo "MATH_DONE $(date)"
