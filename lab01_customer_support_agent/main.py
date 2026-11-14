import json
import os

from config import LOG_FILE, LOG_TO_STDERR, MAX_TURNS, MODEL, anthropic_client, console
from constants.claude_stop_reasons import END_TURN, TOOL_USE
from helpers.agent_logger import (
    log_final_answer,
    log_iteration,
    log_response,
    log_tool_result,
    log_user_query,
    logger,
    setup_agent_logger,
)
from helpers.claude_response_helpers import is_text_block, is_tool_use_block
from helpers.console_helpers import BOLD, CYAN, DIM, RED, RESET, clear_screen, print_final_answer, show_menu
from tools import ALL_TOOLS, TOOL_HANDLERS

TEST_QUERIES = [
    "Hi, I'm Maria Santos (CUST-1001). Can you check the status of my order ORD-5501?",
    "I'd like a refund for order ORD-5501. The headphones arrived damaged.",
    "I'm James Chen, customer CUST-1002. I want a refund for my monitor order ORD-5503 — it has dead pixels.",
    "I've been going back and forth on this for days. I want to talk to a real person.",
    "I'm Maria Santos, CUST-1001. My headphones from ORD-5501 arrived damaged and I need a refund. Also, "
    "can you check if my other order ORD-5502 has been delivered?",
    # order not found
    "Hi, I'm Jayden, can you tell me what is the status for the order number ORD-2712?",
    # request refund for shipped order
    "Hi, I'm Jack and my email is james.chen@example.com, I want to refund for order ORD-5504",
]


def load_system_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
    with open(prompt_path) as f:
        content = f.read()
    return content


def execute_tool(tool_name: str, tool_input: dict):
    tool_handler = TOOL_HANDLERS.get(tool_name)

    if not tool_handler:
        return {
            "is_error": True,
            "content": {
                "is_tool_found": False,
                "message": f"Unknown tool: {tool_name}",
            },
        }

    return tool_handler(**tool_input)


def run_agent(user_input):
    system_prompt = load_system_prompt()

    MESSAGES = [
        {
            "role": "user",
            "content": user_input,
        }
    ]

    log_user_query(user_input)

    for i in range(MAX_TURNS):
        log_iteration(i + 1, MAX_TURNS, MESSAGES)

        try:
            with console.status("Processing request...", spinner="dots"):
                response = anthropic_client.messages.create(
                    model=MODEL, max_tokens=1024, system=system_prompt, tools=ALL_TOOLS, messages=MESSAGES
                )
        except Exception as e:
            logger.exception("API call failed")
            error_msg = str(e).lower()
            if "credit" in error_msg or "balance" in error_msg:
                print(f"\n{RED}{BOLD}API credit balance is too low.{RESET}")
                print(f"{DIM}Add credits at https://console.anthropic.com{RESET}")
            elif "usage limit" in error_msg or "rate limit" in error_msg:
                # Extract the human-readable message from the error
                import re

                match = re.search(r'"message"\s*:\s*"([^"]+)"', str(e))
                friendly_msg = match.group(1) if match else str(e)
                print(f"\n{RED}{BOLD}{friendly_msg}{RESET}")
                print(f"{DIM}Check your limits at https://console.anthropic.com{RESET}")
            else:
                print(f"\n{RED}{BOLD}Error: {e}{RESET}")
            return

        log_response(response)

        if response.stop_reason == END_TURN:
            answer = "".join(block.text for block in response.content if is_text_block(block))
            log_final_answer(answer)
            print_final_answer(console, answer)
            break

        elif response.stop_reason == TOOL_USE:
            tool_result_blocks = []

            for block in response.content:
                if is_tool_use_block(block):
                    tool_result = execute_tool(block.name, block.input)
                    log_tool_result(block.name, block.id, tool_result)

                    tool_result_blocks.append(
                        {
                            "is_error": bool(tool_result.get("is_error")),
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(tool_result.get("content")),
                        }
                    )

            MESSAGES.append({"role": "assistant", "content": response.content})
            MESSAGES.append({"role": "user", "content": tool_result_blocks})

        else:
            logger.error("Unexpected stop_reason: %s", response.stop_reason)
            raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")

    else:
        logger.error("Agent reached max iterations (%d)", MAX_TURNS)
        raise RuntimeError(f"Agent reached max iterations ({MAX_TURNS})")


def main():
    setup_agent_logger(LOG_FILE, also_stderr=LOG_TO_STDERR)
    clear_screen()
    show_menu(TEST_QUERIES)

    while True:
        user_input = input(f"{CYAN}You > {RESET}").strip()

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            break

        if user_input.lower() == "c":
            clear_screen()
            show_menu(TEST_QUERIES)
            continue

        if user_input.isdigit() and 1 <= int(user_input) <= len(TEST_QUERIES):
            user_input = TEST_QUERIES[int(user_input) - 1]
            print(f"  {DIM}→ {user_input}{RESET}")

        run_agent(user_input)


if __name__ == "__main__":
    main()
