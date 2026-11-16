import json
from typing import Any


def render_facts_block(facts: dict[str, Any], *, tag: str, instruction: str) -> str:
    known = {name: value for name, value in facts.items() if value}
    if not known:
        return ""
    return f"\n\n{instruction}\n<{tag}>\n{json.dumps(known, indent=2)}\n</{tag}>"
