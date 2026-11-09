"""Stub for the `vllm` package.

`agentflow/engine/vllm.py` does `import vllm` at module import time but never
uses it (it talks to the server through the OpenAI client).  On a machine where
the vLLM wheel is not installed (e.g. a laptop talking to a remote endpoint),
this empty module keeps the import working.
"""

__version__ = "0.0.0-stub"
