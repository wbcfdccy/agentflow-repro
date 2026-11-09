import re

pat = r'.*?execution\s*=\s*tool\.execute\([^\n]*\)\s*(?:\n|$)'

cases = {
    "single": 'execution = tool.execute(query="a")',
    "multi_before": 'x = 48*3/8\nexecution = tool.execute(query="rem")\nprint(x)',
    "multi_before_fstring": 'x = 48*3/8\nexecution = tool.execute(query=f"rem {x}")\nprint(x)',
    "two_calls": 'execution = tool.execute(query="a")\nexecution = tool.execute(query="b")',
    "func_only": 'def f(x):\n    return x\n',
}

for k, v in cases.items():
    blocks = re.findall(pat, v, re.DOTALL)
    print("==", k)
    for i, b in enumerate(blocks):
        print(f"   block{i}: {b!r}")
    print("   count:", len(blocks))
