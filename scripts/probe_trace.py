"""Offline probe of AgentFlow's Planner -> Executor -> Verifier loop.

Runs the REAL Solver / Planner / Executor / Verifier / Memory code from the
checkout, but swaps the LLM engines for scripted fakes so that no API key is
needed.  Everything that crosses a component boundary is recorded verbatim.

Outputs: ./trace/run_*/calls.json, solver_output.json, prompt/response .txt
"""

from __future__ import annotations

import copy
import json
import logging  # noqa: F401  (imported before sys.path shadowing)
import os
import re
import sys
import textwrap
from pathlib import Path

PROJECT = Path(os.environ.get("AF_ROOT", str(Path.home() / "AgentFlow")))
PKG = PROJECT / "agentflow"
HERE = Path(__file__).resolve().parent
TRACE = HERE / "trace"
TRACE.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(PKG))

from agentflow.models import planner as planner_mod  # noqa: E402
from agentflow.models import verifier as verifier_mod  # noqa: E402
from agentflow.models import executor as executor_mod  # noqa: E402
from agentflow.models.formatters import (  # noqa: E402
    MemoryVerification,
    NextStep,
    QueryAnalysis,
    ToolCommand,
)
from agentflow.models.memory import Memory  # noqa: E402
from agentflow.models.planner import Planner  # noqa: E402
from agentflow.models.verifier import Verifier  # noqa: E402
from agentflow.models.executor import Executor  # noqa: E402
from agentflow.solver import Solver  # noqa: E402

TOOLS = [
    "Generalist_Solution_Generator_Tool",
    "Python_Code_Generator_Tool",
    "Ground_Google_Search_Tool",
    "Wikipedia_RAG_Search_Tool",
]

# --------------------------------------------------------------------------
# fake tool
# --------------------------------------------------------------------------
class DummyTool:
    """Mimics the tool interface used by Executor.execute_tool_command()."""

    def __init__(self, name: str):
        self.name = name
        self.output_dir = None

    def set_custom_output_dir(self, d):
        self.output_dir = d

    def execute(self, query=None, **kwargs):
        if "Python" in self.name:
            return {"generated_code": "print(48 - 48*3/8 - 12)", "result": 18.0,
                    "error": None}
        if "Generalist" in self.name:
            return {"answer": "18 copies are left.", "confidence": "high"}
        return [{"query": query, "snippet": "mock search result", "score": 0.91}]


def tool_metadata() -> dict:
    """Shaped exactly like Initializer.toolbox_metadata entries."""
    md = {}
    for t in TOOLS:
        md[t] = {
            "tool_name": t,
            "tool_description": "A generalized tool that answers the query step by step."
            if "Generalist" in t else "A specialized tool.",
            "tool_version": "1.0.0",
            "input_types": {"query": "str - the query for the tool"},
            "output_type": "str - the tool output",
            "demo_commands": [{"command": 'execution = tool.execute(query="...")',
                               "description": "demo"}],
            "user_metadata": {"limitation": "may hallucinate", "best_practice": "be specific"},
            "require_llm_engine": True,
        }
    return md


# --------------------------------------------------------------------------
# scripted fake engine
# --------------------------------------------------------------------------
class Recorder:
    def __init__(self):
        self.calls = []

    def add(self, component, model, prompt, response, fmt):
        self.calls.append({
            "seq": len(self.calls) + 1,
            "component": component,
            "model": model,
            "response_format": getattr(fmt, "__name__", None),
            "prompt": prompt,
            "response": response if isinstance(response, str) else repr(response),
        })


def component_of(fmt) -> str:
    if fmt is QueryAnalysis:
        return "planner.analyze_query (fixed engine)"
    if fmt is NextStep:
        return "planner.generate_next_step (main engine)"
    if fmt is ToolCommand:
        return "executor.generate_tool_command"
    if fmt is MemoryVerification:
        return "verifier.verificate_context (fixed engine)"
    return "planner.generate_final/direct_output (fixed engine)"


class Script:
    """Deterministic answers keyed by which call is being made."""

    def __init__(self, mode: str, text_mode: bool):
        self.mode = mode          # "A": normal 2-step run, "B": invalid tool
        self.text_mode = text_mode  # True = dashscope/vLLM behaviour (raw text)
        self.n_next = 0
        self.n_verify = 0
        self.n_cmd = 0

    # --- planner ---------------------------------------------------------
    def next_step(self, prompt: str):
        self.n_next += 1
        if self.mode == "B" and self.n_next == 1:
            tool = "Web_RAG_Search_Tool"       # NOT in TOOLS on purpose
            sub = "Search the web for the book price"
        elif self.n_next == 1:
            tool = "Python_Code_Generator_Tool"
            sub = "Compute 48 - 48*3/8 - 12 and return the number"
        else:
            tool = "Generalist_Solution_Generator_Tool"
            sub = "State how many copies are left, using the computed number"
        ctx = "query='A bookstore had 48 copies...'; previous result: 18.0"
        if self.text_mode:
            return textwrap.dedent(f"""\
                Justification: The goal needs {tool}.
                Context: {ctx}
                Sub-Goal: {sub}
                Tool Name: {tool}
                """)
        return NextStep(justification="because", context=ctx, sub_goal=sub, tool_name=tool)

    # --- executor --------------------------------------------------------
    def tool_command(self, prompt: str):
        self.n_cmd += 1
        m = re.search(r"\*\*Tool Name:\*\* (\S+)", prompt)
        tool = m.group(1) if m else "Unknown"
        code = f'execution = tool.execute(query="compute 48 - 48*3/8 - 12")'
        if self.text_mode:
            return textwrap.dedent(f"""\
                Analysis: Need one call for {tool}.
                Command Explanation: The tool takes a query string.
                Generated Command:
                ```python
                {code}
                ```
                """)
        return ToolCommand(analysis="one call", explanation="query string",
                           command=code)

    # --- verifier --------------------------------------------------------
    def verify(self):
        self.n_verify += 1
        stop = self.n_verify >= 2
        analysis = (f"(mock verifier round {self.n_verify}) Memory contains the "
                    f"computed result; completeness={'yes' if stop else 'no'}.")
        if self.text_mode:
            return f"Explanation: {analysis}\nConclusion: {'STOP' if stop else 'CONTINUE'}"
        return MemoryVerification(analysis=analysis, stop_signal=stop)


class FakeEngine:
    def __init__(self, model, script, recorder):
        self.model = model
        self.script = script
        self.rec = recorder

    def __call__(self, content, **kwargs):
        fmt = kwargs.get("response_format")
        prompt = content if isinstance(content, str) else "\n".join(str(c) for c in content)

        if fmt is QueryAnalysis:
            resp = ("Concise Summary: arithmetic word problem\n"
                    "Required Skills: arithmetic\nRelevant Tools: python coder\n"
                    "Additional Considerations: none")
        elif fmt is NextStep:
            resp = self.script.next_step(prompt)
        elif fmt is ToolCommand:
            resp = self.script.tool_command(prompt)
        elif fmt is MemoryVerification:
            resp = self.script.verify()
        else:
            resp = "FINAL ANSWER: 18 copies are left."

        self.rec.add(component_of(fmt), self.model, prompt, resp, fmt)
        return resp


# --------------------------------------------------------------------------
# memory that snapshots itself after every add_action
# --------------------------------------------------------------------------
class LoggingMemory(Memory):
    def __init__(self):
        super().__init__()
        self.snapshots = []

    def add_action(self, *a, **k):
        super().add_action(*a, **k)
        self.snapshots.append(copy.deepcopy(self.actions))


def build(text_mode: bool, mode: str, recorder: Recorder):
    script = Script(mode, text_mode)

    def make_engine(model_string=None, **kwargs):
        return FakeEngine(model_string, script, recorder)

    planner_mod.create_llm_engine = make_engine
    verifier_mod.create_llm_engine = make_engine
    executor_mod.create_llm_engine = make_engine

    md = tool_metadata()
    planner = Planner(llm_engine_name="mock-planner-7b(vllm)",
                      llm_engine_fixed_name="mock-fixed(dashscope)",
                      toolbox_metadata=md, available_tools=TOOLS, verbose=True)
    verifier = Verifier(llm_engine_name="mock-verifier(dashscope)",
                        llm_engine_fixed_name="mock-fixed(dashscope)",
                        toolbox_metadata=md, available_tools=TOOLS, verbose=True)
    executor = Executor(llm_engine_name="mock-executor(dashscope)",
                        root_cache_dir=str(TRACE / "cache"), verbose=True,
                        tool_instances_cache={t: DummyTool(t) for t in TOOLS})
    memory = LoggingMemory()
    solver = Solver(planner=planner, verifier=verifier, memory=memory,
                    executor=executor, output_types="final,direct",
                    max_steps=4, max_time=300, verbose=True,
                    root_cache_dir=str(TRACE / "cache"))
    return solver, memory, script, recorder


QUESTION = ("A bookstore had 48 copies of a new book. On Monday it sold 3/8 of "
            "them; on Tuesday it sold 12 more. How many copies are left?")


def dump_run(name: str, text_mode: bool, mode: str):
    rec = Recorder()
    solver, memory, script, rec = build(text_mode, mode, rec)
    out = solver.solve(QUESTION, None)

    d = TRACE / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "calls.json").write_text(json.dumps(rec.calls, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
    try:
        (d / "solver_output.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        (d / "solver_output.err.txt").write_text(str(e), encoding="utf-8")
    (d / "memory_snapshots.json").write_text(
        json.dumps(memory.snapshots, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")

    # one file per boundary-crossing string
    for c in rec.calls:
        tag = f"call{c['seq']:02d}"
        (d / f"{tag}.prompt.txt").write_text(c["prompt"], encoding="utf-8")
        (d / f"{tag}.response.txt").write_text(str(c["response"]), encoding="utf-8")
    (d / "index.json").write_text(json.dumps(
        [{k: c[k] for k in ("seq", "component", "model", "response_format")}
         for c in rec.calls], ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n########## {name}: {len(rec.calls)} LLM calls, "
          f"{len(memory.snapshots)} memory snapshots ##########")
    for c in rec.calls:
        print(f"  [{c['seq']:02d}] {c['component']}  (fmt={c['response_format']})")
    return rec, memory, out


# --------------------------------------------------------------------------
# unit checks of the parsers (the "is the verifier trustworthy?" part)
# --------------------------------------------------------------------------
def parse_checks():
    checks = []
    tricky = [
        "Explanation: The memory is incomplete.\nConclusion: CONTINUE",
        "**Conclusion: STOP**",
        "I would not stop here, more searching is needed.",
        "The answer is probably right, but let's continue.",
        "Conclusion: MAYBE",
    ]
    for t in tricky:
        checks.append({"input": t,
                       "extract_conclusion": list(Verifier.extract_conclusion(None, t))})

    # planner parsing: clean text vs hallucinated / messy
    p = Planner(llm_engine_name="x", llm_engine_fixed_name="x",
                toolbox_metadata=tool_metadata(), available_tools=TOOLS)
    samples = [
        "Justification: x\nContext: ctx\nSub-Goal: do it\nTool Name: Ground_Google_Search_Tool",
        "Context: ctx\nSub-Goal: do it\nTool Name: Ground Google Search Tool",
        "Context: ctx\nSub-Goal: do it\nTool Name: Magic_Tool",
        "**Context:** ctx\n**Sub-Goal:** do it\n**Tool Name:** Python_Code_Generator_Tool",
    ]
    for s in samples:
        checks.append({"input": s,
                       "extract_context_subgoal_and_tool": list(
                           p.extract_context_subgoal_and_tool(s))})

    # executor command extraction: fenced block without the exact prefix
    e = Executor(llm_engine_name="x", root_cache_dir=str(TRACE / "cache"))
    for s in [
        "Generated Command:\n```python\nexecution = tool.execute(query=\"a\")\n```",
        "```python\nexecution = tool.execute(query=\"b\")\n```",
        "I will not call the tool.\nGenerated Command:\n```python\npass\n```",
    ]:
        checks.append({"input": s,
                       "extract_explanation_and_command": list(
                           e.extract_explanation_and_command(s))})

    (TRACE / "parse_checks.json").write_text(
        json.dumps(checks, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    for c in checks:
        print("PARSE:", json.dumps(c, ensure_ascii=False, default=str)[:300])


if __name__ == "__main__":
    dump_run("run_A_text_2steps", text_mode=True, mode="A")
    dump_run("run_B_structured_gpt4o", text_mode=False, mode="A")
    dump_run("run_C_invalid_tool", text_mode=True, mode="B")
    parse_checks()
