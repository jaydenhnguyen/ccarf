from typing import Any, Literal, TypedDict


class ToolSuccessResult(TypedDict):
    is_error: Literal[False]
    content: dict[str, Any]


class ToolErrorResult(TypedDict):
    is_error: Literal[True]
    error_category: str
    is_retryable: bool
    content: dict[str, Any]


ToolResult = ToolSuccessResult | ToolErrorResult
