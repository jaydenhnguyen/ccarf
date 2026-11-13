from dataclasses import dataclass


@dataclass
class Description:
    intro: str
    when_to_use: str
    when_to_not_use: str
    input: str | None = None
    example: str | None = None
    other: str | None = None


def tool_description_template(params: Description) -> str:
    parts = [
        params.intro.strip(),
        f"WHEN TO USE: {params.when_to_use}",
        f"WHEN NOT TO USE: {params.when_to_not_use}",
    ]
    if params.input:
        parts.append(f"INPUT: {params.input}")
    if params.example:
        parts.append(f"EXAMPLE: {params.example}")
    if params.other:
        parts.append(params.other)
    return "\n".join(parts)
