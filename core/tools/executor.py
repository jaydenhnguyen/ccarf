import json
import time
from collections.abc import Callable

from core.agent_logger import logger
from core.tools.errors import INTERNAL, TRANSIENT, VALIDATION, ToolError
from core.tools.results import DEFAULT_RETRY_POLICY, RetryPolicy, ToolResult

RETRY_BASE_DELAY_SECONDS = 0.5

ToolHandler = Callable[..., ToolResult]


class ToolExecutor:
    def __init__(self, handlers: dict[str, ToolHandler], retry_policies: dict[str, RetryPolicy] | None = None):
        self.handlers = handlers
        self.retry_policies = retry_policies or {}

    def execute(self, tool_name: str, tool_input: dict, call_counts: dict[str, int]) -> ToolResult:
        tool_handler = self.handlers.get(tool_name)

        if not tool_handler:
            return {
                "is_error": True,
                "error_category": VALIDATION,
                "is_retryable": False,
                "content": {
                    "is_tool_found": False,
                    "message": f"Unknown tool: {tool_name}",
                },
            }

        policy = self.retry_policies.get(tool_name, DEFAULT_RETRY_POLICY)
        call_counts[tool_name] = call_counts.get(tool_name, 0) + 1

        if policy["retry_by"] == "code":
            return _run_with_code_retry(tool_name, tool_handler, tool_input, policy["max_attempts"])
        if policy["retry_by"] == "model":
            return _run_with_model_retry(
                tool_name, tool_handler, tool_input, policy["max_attempts"], call_counts[tool_name]
            )
        return _run_once(tool_name, tool_handler, tool_input)


def to_tool_result_block(tool_use_id: str, result: ToolResult) -> dict:
    error_fields = (
        {
            "error_category": result["error_category"],
            "is_retryable": result["is_retryable"],
        }
        if result["is_error"]
        else {}
    )

    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "is_error": result["is_error"],
        "content": json.dumps({**result["content"], **error_fields}),
    }


def _call_handler(tool_name: str, handler: ToolHandler, tool_input: dict) -> ToolResult:
    try:
        return handler(**tool_input)
    except ToolError as e:
        return {
            "is_error": True,
            "error_category": e.category,
            "is_retryable": e.retryable,
            "content": {**e.details, "message": e.message},
        }
    except TypeError as e:
        logger.warning("   ! %s called with invalid arguments: %s", tool_name, e)
        return {
            "is_error": True,
            "error_category": VALIDATION,
            "is_retryable": False,
            "content": {"message": f"Invalid arguments for {tool_name}: {e}"},
        }
    except TimeoutError:
        return {
            "is_error": True,
            "error_category": TRANSIENT,
            "is_retryable": True,
            "content": {"message": f"{tool_name} timed out. The result is unknown, not empty."},
        }
    except Exception:
        logger.exception("   ! %s crashed", tool_name)
        return {
            "is_error": True,
            "error_category": INTERNAL,
            "is_retryable": False,
            "content": {"message": f"{tool_name} failed due to an internal error."},
        }


def _is_transient(result: ToolResult) -> bool:
    return result["is_error"] and result["error_category"] == TRANSIENT and result["is_retryable"]


def _run_with_code_retry(tool_name: str, handler: ToolHandler, tool_input: dict, max_attempts: int) -> ToolResult:
    for attempt in range(1, max_attempts + 1):
        result = _call_handler(tool_name, handler, tool_input)
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


def _run_with_model_retry(
    tool_name: str, handler: ToolHandler, tool_input: dict, max_attempts: int, attempt: int
) -> ToolResult:
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

    result = _call_handler(tool_name, handler, tool_input)
    if _is_transient(result):
        result["is_retryable"] = attempt < max_attempts
        result["content"]["attempt"] = attempt
        result["content"]["max_attempts"] = max_attempts
    return result


def _run_once(tool_name: str, handler: ToolHandler, tool_input: dict) -> ToolResult:
    result = _call_handler(tool_name, handler, tool_input)
    if result["is_error"]:
        result["is_retryable"] = False
    return result
