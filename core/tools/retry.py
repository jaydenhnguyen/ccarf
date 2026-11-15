"""Retry strategies. They retry any zero-arg call that returns a ToolResult - they don't know about handlers."""

import time
from collections.abc import Callable
from typing import Literal, TypedDict

from core.agent_logger import logger
from core.tools.errors import TRANSIENT
from core.tools.results import ToolResult

RETRY_BASE_DELAY_SECONDS = 0.5

type ToolCall = Callable[[], ToolResult]


class RetryPolicy(TypedDict):
    retry_by: Literal["code", "model", "none"]
    max_attempts: int


DEFAULT_RETRY_POLICY: RetryPolicy = {"retry_by": "none", "max_attempts": 1}


def run_with_policy(tool_name: str, call: ToolCall, policy: RetryPolicy, attempt: int) -> ToolResult:
    """attempt = how many times Claude has called this tool in the conversation (used by "model" retry)."""
    if policy["retry_by"] == "code":
        return _run_with_code_retry(tool_name, call, policy["max_attempts"])
    if policy["retry_by"] == "model":
        return _run_with_model_retry(tool_name, call, policy["max_attempts"], attempt)
    return _run_once(call)


def _is_transient(result: ToolResult) -> bool:
    return result["is_error"] and result["error_category"] == TRANSIENT and result["is_retryable"]


def _run_with_code_retry(tool_name: str, call: ToolCall, max_attempts: int) -> ToolResult:
    for attempt in range(1, max_attempts + 1):
        result = call()
        if not _is_transient(result):
            return result
        if attempt < max_attempts:
            delay = RETRY_BASE_DELAY_SECONDS * 2 ** (attempt - 1)
            logger.info(
                "   ↻ %s transient error, code retry %d/%d in %.1fs", tool_name, attempt + 1, max_attempts, delay
            )
            time.sleep(delay)

    result["is_retryable"] = False
    result["content"]["attempts"] = max_attempts
    return result


def _run_with_model_retry(tool_name: str, call: ToolCall, max_attempts: int, attempt: int) -> ToolResult:
    if attempt > max_attempts:
        return {
            "is_error": True,
            "error_category": TRANSIENT,
            "is_retryable": False,
            "content": {
                "attempt": attempt,
                "max_attempts": max_attempts,
                "message": f"{tool_name} retry limit reached ({max_attempts}). Do not call it again.",
            },
        }

    result = call()
    if _is_transient(result):
        result["is_retryable"] = attempt < max_attempts
        result["content"]["attempt"] = attempt
        result["content"]["max_attempts"] = max_attempts
    return result


def _run_once(call: ToolCall) -> ToolResult:
    result = call()
    if result["is_error"]:
        result["is_retryable"] = False
    return result
