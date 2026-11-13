import os

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def show_menu(test_queries):
    print(f"{BOLD}Lab 01 - Customer Support Resolution Agent{RESET}\n")
    for i, query in enumerate(test_queries, 1):
        print(f"  {DIM}{i}. {query}{RESET}")
    print(f"  {DIM}c. Clear screen{RESET}")
    print(f"  {DIM}q. Quit{RESET}")
    print(f"\n{DIM}Or type a custom message.{RESET}\n")
