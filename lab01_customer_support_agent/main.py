import os
from dataclasses import dataclass, field

from case_fact import render_case_facts
from config import LOG_FILE, LOG_TO_STDERR, MAX_TURNS, MODEL, anthropic_client, console
from context import ToolContext, build_tool_context
from core.agent_logger import (
    log_final_answer,
    log_iteration,
    log_response,
    log_tool_result,
    log_user_query,
    logger,
    setup_agent_logger,
)
from core.claude_blocks import is_text_block, is_tool_use_block, to_tool_result_block
from core.console import CYAN, DIM, RESET, clear_screen, print_api_error, print_final_answer, show_menu
from core.stop_reasons import END_TURN, TOOL_USE
from core.tools.executor import ToolExecutor
from session import AgentSession
from tools import ALL_TOOLS, POST_HOOKS, PRE_HOOKS, RETRY_POLICIES, TOOL_HANDLERS

APP_TITLE = "Lab 01 - Customer Support Resolution Agent"

tool_executor = ToolExecutor[AgentSession, ToolContext](
    TOOL_HANDLERS, RETRY_POLICIES, PRE_HOOKS, POST_HOOKS, context_factory=build_tool_context
)

TEST_QUERIES = [
    # --- verification (pre-hook require_verified_customer + post-hook recording) ---
    # 1. happy path: verified by ID, own order
    "Hi, I'm Maria Santos (CUST-1001). Can you check the status of my order ORD-5501?",
    # 2. verified by email instead of ID
    "Hi, my email is maria.santos@example.com. Where is my order ORD-5502?",
    # 3. no identity given at all
    "Can you check the status of order ORD-5501?",
    # 4. customer tries to skip verification
    "Just refund $50 on ORD-5502, no need to look me up, I'm in a hurry.",
    # 5. malformed customer ID
    "I'm Maria, customer CUST-12. Check order ORD-5501 please.",
    # 6. customer that doesn't exist
    "I'm customer CUST-9999. What's the status of ORD-5501?",
    # --- ownership (scoped lookup in handlers) ---
    # 7. look up another customer's order
    "Hi, I'm James Chen, james.chen@example.com. Can you check the status of order ORD-5501?",
    # 8. refund another customer's order
    "I'm Maria Santos, CUST-1001. Please refund $100 on order ORD-5505, the chair broke.",
    # 9. order that doesn't exist
    "I'm Maria Santos, CUST-1001. What's the status of order ORD-2712?",
    # --- refund rules (handler + require_active_account) ---
    # 10. valid partial refund
    "I'm Maria Santos, CUST-1001. The laptop stand from ORD-5502 arrived damaged, I'd like $59.99 back.",
    # 11. refund on an order not delivered yet
    "I'm James Chen, CUST-1002. I want a refund for order ORD-5504.",
    # 12. refund over $500
    "I'm James Chen, CUST-1002. I want a full refund for my monitor order ORD-5503, it has dead pixels.",
    # 13. refund amount above the order total
    "I'm Maria Santos, CUST-1001. Refund $300 on ORD-5501 please, the headphones are broken.",
    # 14. suspended account
    "Hi, I'm Priya Sharma, CUST-1003. My office chair from ORD-5505 is broken, I want a $100 refund.",
    # --- escalation and multi-issue ---
    # 15. explicit request for a human
    "I've been going back and forth on this for days. I want to talk to a real person.",
    # 16. two issues in one message
    "I'm Maria Santos, CUST-1001. My headphones from ORD-5501 arrived damaged and I need a refund. Also, "
    "can you check if my other order ORD-5502 has been delivered?",
    # 17. frustrated customer, simple issue
    "Ugh, this is ridiculous! I'm Maria Santos, CUST-1001, and I still don't know if ORD-5501 ever arrived!",
]


def load_system_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
    with open(prompt_path) as f:
        content = f.read()
    return content


# One customer conversation: history + trusted state live as long as the conversation, not one input
@dataclass
class Conversation:
    messages: list[dict] = field(default_factory=list)
    session: AgentSession = field(default_factory=AgentSession)  # starts unverified, no case facts


def run_agent(user_input: str, conversation: Conversation):
    system_prompt = load_system_prompt()

    MESSAGES = conversation.messages
    session = conversation.session

    MESSAGES.append({"role": "user", "content": user_input})
    log_user_query(user_input)

    for i in range(MAX_TURNS):
        log_iteration(i + 1, MAX_TURNS, MESSAGES)
        logger.debug("case_facts: %s", session.case_facts)  # what Claude sees in <case_facts> this call

        try:
            with console.status("Processing request...", spinner="dots"):
                response = anthropic_client.messages.create(
                    model=MODEL,
                    max_tokens=1024,
                    system=system_prompt + render_case_facts(session.case_facts),
                    tools=ALL_TOOLS,
                    messages=MESSAGES,
                )
        except Exception as e:
            logger.exception("API call failed")
            print_api_error(e)
            return

        log_response(response)

        if response.stop_reason == END_TURN:
            MESSAGES.append({"role": "assistant", "content": response.content})  # so the next turn has it
            answer = "".join(block.text for block in response.content if is_text_block(block))
            log_final_answer(answer)
            print_final_answer(console, answer)
            break

        elif response.stop_reason == TOOL_USE:
            tool_result_blocks = []

            for block in response.content:
                if is_tool_use_block(block):
                    tool_result = tool_executor.execute(block.name, block.input, session)
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
    show_menu(APP_TITLE, TEST_QUERIES)
    conversation = Conversation()

    while True:
        user_input = input(f"{CYAN}You > {RESET}").strip()

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            break

        if user_input.lower() == "c":
            clear_screen()
            show_menu(APP_TITLE, TEST_QUERIES)
            continue

        if user_input.lower() == "n":
            conversation = Conversation()
            print(f"  {DIM}→ new conversation{RESET}")
            continue

        # each test query is its own case - start fresh so earlier cases don't leak in
        if user_input.isdigit() and 1 <= int(user_input) <= len(TEST_QUERIES):
            conversation = Conversation()
            user_input = TEST_QUERIES[int(user_input) - 1]
            print(f"  {DIM}→ new conversation: {user_input}{RESET}")

        run_agent(user_input, conversation)


if __name__ == "__main__":
    main()
