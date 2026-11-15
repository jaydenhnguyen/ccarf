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
from helpers.console_helpers import CYAN, DIM, RESET, clear_screen, print_api_error, print_final_answer, show_menu
from tool_executor import execute_tool, to_tool_result_block
from tools import ALL_TOOLS

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


def run_agent(user_input):
    system_prompt = load_system_prompt()

    MESSAGES = [
        {
            "role": "user",
            "content": user_input,
        }
    ]

    log_user_query(user_input)
    tool_call_counts: dict[str, int] = {}  # per run, for retry_by="model"

    for i in range(MAX_TURNS):
        log_iteration(i + 1, MAX_TURNS, MESSAGES)

        try:
            with console.status("Processing request...", spinner="dots"):
                response = anthropic_client.messages.create(
                    model=MODEL, max_tokens=1024, system=system_prompt, tools=ALL_TOOLS, messages=MESSAGES
                )
        except Exception as e:
            logger.exception("API call failed")
            print_api_error(e)
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
                    tool_result = execute_tool(block.name, block.input, tool_call_counts)
                    log_tool_result(block.name, block.id, tool_result)

                    tool_result_blocks.append(to_tool_result_block(block.id, tool_result))

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
