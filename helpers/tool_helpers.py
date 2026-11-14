from dataclasses import dataclass


@dataclass
class Description:
    intro: str
    when_to_use: str
    when_to_not_use: str
    returns_success: str  # required: every tool has a success result
    returns_empty: str | None = None  # tool ran fine but found nothing (valid result, not an error)
    returns_error: str | None = None  # tool could not complete (is_error result)
    input: str | None = None
    example: str | None = None
    other: str | None = None


def _returns_line(params: Description) -> str:
    outcomes = [f"Success: {params.returns_success}"]
    if params.returns_empty:
        outcomes.append(f"Empty: {params.returns_empty}")
    if params.returns_error:
        outcomes.append(f"Error: {params.returns_error}")
    return "RETURNS: " + " | ".join(outcomes)


def tool_description_template(params: Description) -> str:
    parts = [
        params.intro.strip(),
        f"WHEN TO USE: {params.when_to_use}",
        f"WHEN NOT TO USE: {params.when_to_not_use}",
        _returns_line(params),
    ]
    if params.input:
        parts.append(f"INPUT: {params.input}")
    if params.example:
        parts.append(f"EXAMPLE: {params.example}")
    if params.other:
        parts.append(params.other)
    return "\n".join(parts)
