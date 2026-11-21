import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

SERVER = Path(__file__).parent / "server.py"
load_dotenv(Path(__file__).parent.parent / ".env")
PROTOCOL_VERSION = "2025-11-25"

CYAN, GREEN, YELLOW, DIM, BOLD, RESET = "\033[96m", "\033[92m", "\033[93m", "\033[2m", "\033[1m", "\033[0m"

# stands in for the FE login: in a real system the user signs in (OIDC) and the client receives their token.
# the client only holds tokens; it does NOT know roles (only the backend does)
LOGIN_USERS: list[tuple[str, str | None]] = [
    ("Carl", "tok-carl"),
    ("Alice", "tok-alice"),
    ("Hana", "tok-hana"),
    ("Mallory (token the backend doesn't know)", "tok-fake"),
    ("Nobody (no user token sent)", None),
]

CLIENT_TOKEN_MODES = ("valid", "wrong", "missing")


class RawClient:
    def __init__(self) -> None:
        # env={}: the server gets no configuration or secrets from us; it reads its own config
        self.proc = subprocess.Popen(
            [sys.executable, str(SERVER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env={}
        )
        self.next_id = 1

        self.valid_client_token = os.getenv("DOCS_MCP_CLIENT_TOKEN")  # MCP client's own credential
        self.client_token_mode = "valid"
        # nobody is logged in yet: the user token is chosen at login, not read from the env
        self.user_name: str = "nobody (not logged in)"
        self.user_token: str | None = None

    @property
    def client_token(self) -> str | None:
        return {"valid": self.valid_client_token, "wrong": "cli-token-wrong", "missing": None}[self.client_token_mode]

    def _with_token(self, params: dict[str, Any] | None) -> dict[str, Any]:
        params = dict(params or {})
        tokens = {"docs/client_token": self.client_token, "docs/user_token": self.user_token}

        if present := {key: value for key, value in tokens.items() if value}:
            # both credentials go in _meta, set by client code: never in tool arguments
            params["_meta"] = {**params.get("_meta", {}), **present}

        return params

    def _send(self, message: dict[str, Any]) -> None:
        print(f"\n{CYAN}→ client sends{RESET}\n{json.dumps(message, indent=2)}")
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def notify(self, method: str) -> None:
        message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}  # notification: no id, no reply
        if params := self._with_token(None):
            message["params"] = params
        self._send(message)

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        message: dict[str, Any] = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        if params := self._with_token(params):
            message["params"] = params

        self.next_id += 1
        self._send(message)

        line = self.proc.stdout.readline()
        if not line:  # stdout closed: the server exited (e.g. refused to start); its reason is on stderr above
            raise SystemExit(f"server exited with code {self.proc.wait()} before replying")

        response = json.loads(line)
        print(f"{GREEN}← server replies{RESET}\n{json.dumps(response, indent=2)}")
        return response

    def handshake(self) -> bool:
        # once per session, as the client app, before any user logs in: carries the client token only
        print(f"\n{DIM}--- handshake (initialize + notifications/initialized){RESET}")
        response = self.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "raw-client", "version": "0.1"},
            },
        )
        if "error" in response:
            print(f"{YELLOW}handshake refused: check DOCS_MCP_CLIENT_TOKEN in .env{RESET}")
            return False
        self.notify("notifications/initialized")
        return True

    def call_tool(self, name: str, arguments: dict[str, Any]) -> None:
        self.request("tools/call", {"name": name, "arguments": arguments})

    def close(self) -> None:
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


def login(client: RawClient) -> None:
    index = choose("Log in as:", [f"{name}  ({token or 'no token'})" for name, token in LOGIN_USERS])
    client.user_name, client.user_token = LOGIN_USERS[index]


def set_client_token_mode(client: RawClient) -> None:
    index = choose("Client token to send:", list(CLIENT_TOKEN_MODES))
    client.client_token_mode = CLIENT_TOKEN_MODES[index]


ACTIONS = [
    "tools/list",
    "resources/list",
    "resources/read docs://index",
    "search_docs (enter a query)",
    "get_doc (enter a doc_id: try DOC-101, DOC-104, DOC-999, abc)",
    "call an unknown tool",
    "get_doc with no arguments",
    "switch logged-in user",
    "change client token (valid / wrong / missing)",
    "quit",
]


def run_action(client: RawClient, action: int) -> None:
    if action == 7:
        login(client)
        return
    if action == 8:
        set_client_token_mode(client)
        return

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


def main() -> None:
    client = RawClient()
    print(f"{DIM}Backend timeout: set SIMULATE_BACKEND_TIMEOUT=1 in .env (applies on the next call).{RESET}")
    try:
        if not client.handshake():
            return
        login(client)
        while True:
            header = f"Logged in as {client.user_name} | client token: {client.client_token_mode}"
            action = choose(header, ACTIONS)
            if action == len(ACTIONS) - 1:
                break
            run_action(client, action)
    except EOFError, KeyboardInterrupt:
        print()
    finally:
        client.close()


if __name__ == "__main__":
    main()
