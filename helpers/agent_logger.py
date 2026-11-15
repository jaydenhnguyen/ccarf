# Developer-facing monitoring/debug log for the agent loop.
import json
import logging
import sys
from pathlib import Path

from helpers.tool_helpers import ToolResult

logger = logging.getLogger("agent")


def setup_agent_logger(log_file: Path, level: int = logging.DEBUG, also_stderr: bool = False) -> logging.Logger:
    if logger.handlers:
        return logger

    log_file.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)-5s %(message)s", datefmt="%H:%M:%S")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if also_stderr:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    logger.setLevel(level)
    logger.propagate = False  # don't duplicate into the root logger
    return logger


# ---------------------------------------------------------------------------
# Formatting: one line per message / block instead of full JSON
# ---------------------------------------------------------------------------


def _short(value, limit: int = 100) -> str:
    """One-line, truncated representation of a str/dict/list."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(text.split())  # collapse newlines/whitespace
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _block_type(block) -> str:
    return block["type"] if isinstance(block, dict) else block.type


def _describe_message(message: dict) -> str:
    """e.g. 'user: text' / 'assistant: thinking, text, tool_use' / 'user: tool_result x2'."""
    content = message["content"]
    if isinstance(content, str):
        return f"{message['role']}: text"
    types = [_block_type(b) for b in content]
    if len(types) > 1 and all(t == types[0] for t in types):
        return f"{message['role']}: {types[0]} x{len(types)}"
    return f"{message['role']}: {', '.join(types) or '(empty)'}"


# ---------------------------------------------------------------------------
# Log events
# ---------------------------------------------------------------------------


def log_user_query(user_input: str) -> None:
    logger.info("=" * 70)
    logger.info("USER QUERY: %s", _short(user_input, 200))


def log_iteration(iteration: int, max_turns: int, messages: list) -> None:
    logger.info("--- Iteration %d/%d ---", iteration, max_turns)
    logger.debug("→ request: %d messages", len(messages))
    for idx, message in enumerate(messages):
        logger.debug("   [%d] %s", idx, _describe_message(message))


def log_response(response) -> None:
    types = ", ".join(_block_type(b) for b in response.content) or "(empty)"
    logger.info("← response: stop_reason=%s  blocks: %s", response.stop_reason, types)

    for block in response.content:
        if block.type == "thinking":
            logger.debug("   💭 thinking: %s", _short(block.thinking))
        elif block.type == "text":
            logger.debug("   💬 text: %s", _short(block.text))
        elif block.type == "tool_use":
            logger.info("   🔧 tool_use: %s(%s)  id=…%s", block.name, _short(block.input, 80), block.id[-6:])
        else:
            logger.debug("   • %s", block.type)


def log_tool_result(tool_name: str, tool_use_id: str, result: ToolResult) -> None:
    """result is the handler's ToolResult: {"is_error", "content"} plus error_category / is_retryable on errors."""
    content = result["content"]
    if result["is_error"]:
        logger.warning(
            "   ✗ %s id=…%s %s retryable=%s: %s",
            tool_name,
            tool_use_id[-6:],
            result["error_category"],
            result["is_retryable"],
            _short(content.get("message", content)),
        )
    else:
        logger.info("   ✓ %s id=…%s %s", tool_name, tool_use_id[-6:], _short(content, 120))


def log_final_answer(answer: str) -> None:
    logger.info("FINAL ANSWER: %s", _short(answer, 200))
