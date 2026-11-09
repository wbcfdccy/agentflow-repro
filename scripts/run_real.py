"""Run the real AgentFlow Solver loop against a vLLM OpenAI-compatible endpoint.

This is the runner used for the reproduction.  It wires the same components as
`test/solve.py`, but with the import layout that actually works for this repo
(`agentflow` = <AF_ROOT>/agentflow/agentflow) and with every engine endpoint
configurable.

Layout expected:

    $AF_ROOT/                     # a clone of https://github.com/lupantech/AgentFlow
    ├── agentflow/
    │   ├── agentflow/            # the package we import
    │   ├── client.py ...
    └── lib/
        └── agentflow -> ../agentflow/agentflow    # symlink/junction

    $AF_ROOT/test/aime24/data/data.json            # benchmark data

Usage:
    python run_real.py --data test/aime24/data/data.json --index 0 \
        --model agentflow-planner-7b --output_types direct --out run.json

Environment:
    AF_ROOT          path to the AgentFlow checkout (default ~/AgentFlow)
    AF_BASE_URL      vLLM endpoint (default http://127.0.0.1:8000/v1)
    DASHSCOPE_API_KEY / OPENAI_API_KEY   when those engines are used
"""

import argparse
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
AF_ROOT = os.environ.get("AF_ROOT", os.path.expanduser("~/AgentFlow"))

sys.path.insert(0, os.path.join(BASE, "stubs"))            # stub `vllm` when not installed
sys.path.insert(0, os.path.join(AF_ROOT, "lib"))          # lib/agentflow -> agentflow/agentflow

DEFAULT_ENDPOINT = os.environ.get("AF_BASE_URL", "http://127.0.0.1:8000/v1")

# The OpenAI SDK can crash while decompressing responses (httpx2 decoder
# mismatch); asking for identity encoding avoids the decoder entirely.
import openai as _openai_mod  # noqa: E402

_OrigOpenAI = _openai_mod.OpenAI


class _PatchedOpenAI(_OrigOpenAI):
    def __init__(self, *args, **kwargs):
        headers = dict(kwargs.get("default_headers") or {})
        headers.setdefault("Accept-Encoding", "identity")
        kwargs["default_headers"] = headers
        super().__init__(*args, **kwargs)


_openai_mod.OpenAI = _PatchedOpenAI

# Wikipedia blocks the default python-wikipedia user agent (403 -> JSONDecodeError).
try:
    import wikipedia as _wiki

    _wiki.USER_AGENT = "agentflow-research/1.0 (benchmark reproduction)"
    if getattr(_wiki, "wikipedia", None) is not None:
        _wiki.wikipedia.USER_AGENT = _wiki.USER_AGENT
except Exception:  # pragma: no cover
    pass

import agentflow.engine.factory as _factory  # noqa: E402

_orig_create = _factory.create_llm_engine


def _create(model_string="", **kwargs):
    if "vllm" in str(model_string) and not kwargs.get("base_url"):
        kwargs["base_url"] = DEFAULT_ENDPOINT
    return _orig_create(model_string, **kwargs)


_factory.create_llm_engine = _create

from agentflow.solver import construct_solver  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", default=None)
    ap.add_argument("--data", default=None)
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--max_steps", type=int, default=4)
    ap.add_argument("--max_time", type=int, default=900)
    ap.add_argument("--model", default=os.environ.get("AF_MODEL", "agentflow-planner-7b"))
    ap.add_argument("--base_url", default=DEFAULT_ENDPOINT)
    ap.add_argument("--tools", default="Base_Generator_Tool,Python_Coder_Tool")
    ap.add_argument("--tool_engines", default=os.environ.get(
        "AF_TOOL_ENGINES", "dashscope-qwen-plus,dashscope-qwen3-coder-flash"))
    ap.add_argument("--fixed", default=os.environ.get("AF_FIXED", "dashscope-qwen-plus"))
    ap.add_argument("--executor", default=os.environ.get("AF_EXECUTOR", "dashscope-qwen-plus"))
    ap.add_argument("--verifier", default=os.environ.get("AF_VERIFIER", "dashscope-qwen-plus"))
    ap.add_argument("--output_types", default="base,final,direct")
    ap.add_argument("--force_format", action="store_true",
                    help="append an <answer> instruction when the dataset lacks one")
    ap.add_argument("--out", default="last_run.json")
    args = ap.parse_args()

    if args.data:
        with open(os.path.join(AF_ROOT, args.data), encoding="utf-8") as f:
            data = json.load(f)
        item = data[args.index]
        question = item.get("query") or item.get("question")
    else:
        question = args.question or "What is the capital of France?"

    if args.force_format and "<answer>" not in question:
        question = question + (
            " When ready, output the final answer enclosed in <answer> and </answer> tags. "
            "For multiple-choice questions, put the option letter (e.g. A) inside the tags."
        )

    tools = [t for t in args.tools.split(",") if t]
    model = args.model if args.model.startswith("vllm-") else f"vllm-{args.model}"
    tool_engines = [e for e in args.tool_engines.split(",") if e]
    if len(tool_engines) < len(tools):
        tool_engines += ["dashscope"] * (len(tools) - len(tool_engines))

    solver = construct_solver(
        llm_engine_name=model,
        enabled_tools=tools,
        tool_engine=tool_engines,
        # [planner_main, planner_fixed, verifier, executor]
        model_engine=["trainable", args.fixed, args.verifier, args.executor],
        output_types=args.output_types,
        max_steps=args.max_steps,
        max_time=args.max_time,
        max_tokens=2048,
        root_cache_dir=os.path.join(BASE, "cache"),
        verbose=True,
        base_url=args.base_url,
        temperature=0.0,
    )

    out = solver.solve(question)
    path = args.out if os.path.isabs(args.out) else os.path.join(BASE, args.out)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)

    print("\n===== SUMMARY =====")
    print("question:", str(question)[:300])
    print("steps:", out.get("step_count"))
    print("tools:", [v.get("tool_name") for v in out.get("memory", {}).values()])
    print("direct_output:", str(out.get("direct_output"))[:600])
    print("saved:", path)


if __name__ == "__main__":
    main()
