from typing import Any, Literal, NotRequired, TypedDict


class ToolSuccess(TypedDict):
    is_error: Literal[False]
    content: dict[str, Any]


class ToolError(TypedDict):
    is_error: Literal[True]
    error_category: str
    is_retryable: bool
    content: dict[str, Any]


ToolResult = ToolSuccess | ToolError


class RetryPolicy(TypedDict):
    retry_by: Literal["code", "model", "none"]
    max_attempts: int


DEFAULT_RETRY_POLICY: RetryPolicy = {"retry_by": "none", "max_attempts": 1}


class Description(TypedDict):
    intro: str
    when_to_use: str
    when_to_not_use: str
    returns_success: str
    returns_empty: NotRequired[str]
    returns_error: NotRequired[str]
    input: NotRequired[str]
    example: NotRequired[str]
    other: NotRequired[str]


def _returns_line(params: Description) -> str:
    outcomes = [f"Success: {params['returns_success']}"]
    if returns_empty := params.get("returns_empty"):
        outcomes.append(f"Empty: {returns_empty}")
    if returns_error := params.get("returns_error"):
        outcomes.append(f"Error: {returns_error}")
    return "RETURNS: " + " | ".join(outcomes)


def tool_description_template(params: Description) -> str:
    parts = [
        params["intro"].strip(),
        f"WHEN TO USE: {params['when_to_use']}",
        f"WHEN NOT TO USE: {params['when_to_not_use']}",
        _returns_line(params),
    ]
    if tool_input := params.get("input"):
        parts.append(f"INPUT: {tool_input}")
    if example := params.get("example"):
        parts.append(f"EXAMPLE: {example}")
    if other := params.get("other"):
        parts.append(other)
    return "\n".join(parts)
