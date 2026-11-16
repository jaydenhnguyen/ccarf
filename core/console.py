import os
import re

from rich.console import Console
from rich.panel import Panel

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def show_menu(title: str, test_queries: list[str]) -> None:
    print(f"{BOLD}{title}{RESET}\n")
    for i, query in enumerate(test_queries, 1):
        print(f"  {DIM}{i}. {query}{RESET}")
    print(f"  {DIM}n. New conversation{RESET}")
    print(f"  {DIM}c. Clear screen{RESET}")
    print(f"  {DIM}q. Quit{RESET}")
    print(f"\n{DIM}Or type a custom message.{RESET}\n")


def print_final_answer(console: Console, text: str) -> None:
    console.print(Panel(text or "[dim](no text)[/dim]", title="Agent", border_style="green"))


def print_api_error(error: Exception) -> None:
    """User-facing message for a failed Anthropic API call (details go to the log separately)."""
    error_msg = str(error).lower()
    if "credit" in error_msg or "balance" in error_msg:
        print(f"\n{RED}{BOLD}API credit balance is too low.{RESET}")
        print(f"{DIM}Add credits at https://console.anthropic.com{RESET}")
    elif "usage limit" in error_msg or "rate limit" in error_msg:
        # Extract the human-readable message from the error
        match = re.search(r'"message"\s*:\s*"([^"]+)"', str(error))
        friendly_msg = match.group(1) if match else str(error)
        print(f"\n{RED}{BOLD}{friendly_msg}{RESET}")
        print(f"{DIM}Check your limits at https://console.anthropic.com{RESET}")
    else:
        print(f"\n{RED}{BOLD}Error: {error}{RESET}")
