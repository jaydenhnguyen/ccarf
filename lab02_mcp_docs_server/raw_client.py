import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SERVER = Path(__file__).parent / "server.py"
PROTOCOL_VERSION = "2025-11-25"

CYAN, GREEN, YELLOW, DIM, BOLD, RESET = "\033[96m", "\033[92m", "\033[93m", "\033[2m", "\033[1m", "\033[0m"

# stands in for the FE login: in a real system the user signs in (OIDC) and the client receives their token.
# the client only holds tokens; it does NOT know roles (only the backend does)
LOGIN_USERS: list[tuple[str, str | None]] = [
    ("Carl", "tok-carl"),
    ("Alice", "tok-alice"),
    ("Hana", "tok-hana"),
    ("Mallory (token the backend doesn't know)", "tok-fake"),
    ("Nobody (no user token)", None),
]


class ServerExitedError(Exception):
    pass


class RawClient:
    def __init__(self, user_token: str | None) -> None:
        # stdio = one server process per user: the user's token goes in the server's env at spawn,
        # exactly like Claude Code does with the "env" block in .mcp.json. Nothing else is passed
        env = {"DOCS_USER_TOKEN": user_token} if user_token else {}
        self.proc = subprocess.Popen(
            [sys.executable, str(SERVER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env
        )
        self.next_id = 1

    def _send(self, message: dict[str, Any]) -> None:
        print(f"\n{CYAN}→ client sends{RESET}\n{json.dumps(message, indent=2)}")
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def notify(self, method: str) -> None:
        self._send({"jsonrpc": "2.0", "method": method})  # notification: no id, no reply

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        message: dict[str, Any] = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        if params is not None:
            message["params"] = params

        self.next_id += 1
        try:
            self._send(message)
            line = self.proc.stdout.readline()
        except BrokenPipeError:
            line = ""
        if not line:  # stdout closed: the server exited (e.g. refused to start); its reason is on stderr above
            raise ServerExitedError(f"server exited with code {self.proc.wait()} before replying")

        response = json.loads(line)
        print(f"{GREEN}← server replies{RESET}\n{json.dumps(response, indent=2)}")
        return response

    def handshake(self) -> None:
        print(f"\n{DIM}--- handshake (initialize + notifications/initialized){RESET}")
        self.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "raw-client", "version": "0.1"},
            },
        )
        self.notify("notifications/initialized")

    def call_tool(self, name: str, arguments: dict[str, Any]) -> None:
        self.request("tools/call", {"name": name, "arguments": arguments})

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.stdin.close()
            self.proc.wait(timeout=5)


def choose(title: str, options: list[str]) -> int:
    print(f"\n{BOLD}{title}{RESET}")
    for number, option in enumerate(options, start=1):
        print(f"  {number}. {option}")
    while True:
        answer = input("> ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return int(answer) - 1
        print(f"pick 1-{len(options)}")


ACTIONS = [
    "tools/list",
    "resources/list",
    "resources/read docs://index",
    "search_docs (enter a query)",
    "get_doc (enter a doc_id: try DOC-101, DOC-104, DOC-999, abc)",
    "call an unknown tool",
    "get_doc with no arguments",
    "log out (switch user)",
    "quit",
]
LOG_OUT, QUIT = len(ACTIONS) - 2, len(ACTIONS) - 1


def run_action(client: RawClient, action: int) -> None:
    match action:
        case 0:
            client.request("tools/list")
        case 1:
            client.request("resources/list")
        case 2:
            client.request("resources/read", {"uri": "docs://index"})
        case 3:
            client.call_tool("search_docs", {"query": input("query> ")})
        case 4:
            client.call_tool("get_doc", {"doc_id": input("doc_id> ")})
        case 5:
            client.call_tool("nope", {})
        case 6:
            client.call_tool("get_doc", {})


def session(user_name: str, user_token: str | None) -> bool:
    """One logged-in user = one server process. Returns False when the user chose to quit."""
    client = RawClient(user_token)
    try:
        client.handshake()
        while True:
            action = choose(f"Logged in as {user_name}", ACTIONS)
            if action in (LOG_OUT, QUIT):
                return action == LOG_OUT
            run_action(client, action)
    except ServerExitedError as error:
        print(f"{YELLOW}{error}{RESET}")
        return True  # back to the login screen
    finally:
        client.close()


def main() -> None:
    print(f"{DIM}Backend timeout: set SIMULATE_BACKEND_TIMEOUT=1 in .env (applies on the next call).{RESET}")
    try:
        while True:
            index = choose("Log in as:", [f"{name}  ({token or 'no token'})" for name, token in LOGIN_USERS])
            if not session(*LOGIN_USERS[index]):
                break
    except EOFError, KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
