import json

from anthropic.types import TextBlock, ThinkingBlock, ToolUseBlock

from core.tools.results import ToolResult


def is_text_block(block: ThinkingBlock | ToolUseBlock | TextBlock) -> bool:
    return block.type == "text"


def is_tool_use_block(block: ThinkingBlock | ToolUseBlock | TextBlock) -> bool:
    return block.type == "tool_use"


def is_thinking_block(block: ThinkingBlock | ToolUseBlock | TextBlock) -> bool:
    return block.type == "thinking"


def to_tool_result_block(tool_use_id: str, result: ToolResult) -> dict:
    """Convert our internal ToolResult into the API's tool_result block (custom fields go inside content)."""
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
