import os
import json
from constants.claude_stop_reasons import END_TURN, TOOL_USE
from helpers.claude_response_helpers import is_text_block, is_tool_use_block, is_thinking_block
from tools import ALL_TOOLS, TOOL_HANDLERS
from config import anthropic_client, MAX_TURNS, console, MODEL
from helpers.console_helpers import clear_screen, show_menu, CYAN, RESET, DIM, RED, BOLD, GREEN, YELLOW
from rich.json import JSON

TEST_QUERIES = [
    "Hi, I'm Maria Santos (CUST-1001). Can you check the status of my order ORD-5501?",
    "I'd like a refund for order ORD-5501. The headphones arrived damaged.",
    "I'm James Chen, customer CUST-1002. I want a refund for my monitor order ORD-5503 — it has dead pixels.",
    "I've been going back and forth on this for days. I want to talk to a real person.",
    "I'm Maria Santos, CUST-1001. My headphones from ORD-5501 arrived damaged and I need a refund. Also, "
    "can you check if my other order ORD-5502 has been delivered?",
]


def load_system_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
    with open(prompt_path, "r") as f:
        content = f.read()
    return content


def execute_tool(tool_name: str, tool_input: dict):
    tool_handler = TOOL_HANDLERS.get(tool_name)

    if not tool_handler:
        return {
            "error": True,
            "errorCategory": "validation",
            "isRetryable": False,
            "message": f"Unknown tool: {tool_name}",
        }

    return tool_handler(**tool_input)


def run_agent(user_input):
    system_prompt = load_system_prompt()

    messages = [{
        "role": "user",
        "content": user_input,
    }]

    for i in range(MAX_TURNS):
        print(f"\n{DIM}--- Iteration {i + 1} ---{RESET}")

        try:
            with console.status("Processing request...", spinner="dots"):
                response = anthropic_client.messages.create(
                    model=MODEL,
                    max_tokens=1024,
                    system=system_prompt,
                    tools=ALL_TOOLS,
                    messages=messages
                )
        except Exception as e:
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

        print(f"  {DIM}stop_reason: {response.stop_reason}{RESET}")

        if response.stop_reason == END_TURN:
            for block in response.content:
                if is_thinking_block(block):
                    print(f"  {GREEN}Agent (thinking): {block.thinking}{RESET}")
                if is_text_block(block):
                    print(f"\n{GREEN}{BOLD}Agent:{RESET} {GREEN}{block.text}{RESET}")
            break

        elif response.stop_reason == TOOL_USE:
            tool_result_blocks = []

            for block in response.content:
                if is_tool_use_block(block):
                    print(f"  {YELLOW}Tool call: {block.name}{RESET}")
                    console.print(JSON(json.dumps(block.input, indent=2)), style="dim")

                    tool_result = execute_tool(block.name, block.input)
                    print(f"  {DIM}Result:{RESET}")
                    console.print(JSON(json.dumps(tool_result, indent=2)), style="dim")

                    tool_result_blocks.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(tool_result),
                    })

                elif is_text_block(block):
                    print(f"  {GREEN}Agent (thinking): {block.text}{RESET}")

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_result_blocks})

        else:
            raise RuntimeError(f"  {RED}Unexpected stop_reason: {response.stop_reason}{RESET}")

    else:
        raise RuntimeError(f"\n{RED}⚠ Agent reached max iterations ({MAX_TURNS}){RESET}")

    print(f"\n{DIM}{'=' * 60}{RESET}\n")


def main():
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
