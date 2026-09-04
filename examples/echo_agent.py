import json
import sys

prompt = sys.stdin.read().strip()
print(json.dumps({"answer": prompt.upper(), "safe": "secret" not in prompt.lower()}))
