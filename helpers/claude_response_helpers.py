from anthropic.types import ThinkingBlock, ToolUseBlock, TextBlock


def is_text_block(block: ThinkingBlock | ToolUseBlock | TextBlock) -> bool:
    return block.type == "text"


def is_tool_use_block(block: ThinkingBlock | ToolUseBlock | TextBlock) -> bool:
    return block.type == "tool_use"


def is_thinking_block(block: ThinkingBlock | ToolUseBlock | TextBlock) -> bool:
    return block.type == "thinking"
