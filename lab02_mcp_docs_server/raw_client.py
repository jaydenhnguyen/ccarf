"""B0 - a hand-written MCP client, no SDK: what a host's MCP client does under the hood.

Spawns server_ref.py as a subprocess (stdio transport) and exchanges newline-delimited JSON-RPC
messages with it. No Claude API call happens here.

Run from the repo root:
    .venv/bin/python lab02_mcp_docs_server/raw_client.py
"""

import json
import subprocess
import sys
from pathlib import Path

SERVER = Path(__file__).parent / "server.py"
PROTOCOL_VERSION = "2025-11-25"  # handshake-era revision (initialize -> initialized -> requests)

CYAN, GREEN, DIM, RESET = "\033[96m", "\033[92m", "\033[2m", "\033[0m"


class RawClient:
    def __init__(self) -> None:
        # stdin/stdout = protocol channel; stderr is inherited so server logs show in this terminal
        self.proc = subprocess.Popen(
            [sys.executable, str(SERVER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
        )
        self.next_id = 1

    def _send(self, message: dict) -> None:
        print(f"\n{CYAN}→ client sends{RESET}\n{json.dumps(message, indent=2)}")
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def request(self, method: str, params: dict | None = None) -> dict:
        message = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        if params is not None:
            message["params"] = params
        self.next_id += 1
        self._send(message)
        response = json.loads(self.proc.stdout.readline())
        print(f"{GREEN}← server replies{RESET}\n{json.dumps(response, indent=2)}")
        return response

    def notify(self, method: str) -> None:
        self._send({"jsonrpc": "2.0", "method": method})  # notification: no id, no reply

    def close(self) -> None:
        self.proc.stdin.close()
        self.proc.wait(timeout=5)


def step(title: str) -> None:
    input(f"\n{DIM}--- {title} (Enter){RESET}")


def main() -> None:
    client = RawClient()
    try:
        step("1. initialize: agree on protocol version and capabilities")
        client.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "raw-client", "version": "0.1"},
            },
        )
        client.notify("notifications/initialized")

        step("2. tools/list: what the host would hand to Claude as `tools`")
        client.request("tools/list")

        step("3. resources/list: what the host's app/UI can read")
        client.request("resources/list")

        step("4. resources/read docs://index")
        client.request("resources/read", {"uri": "docs://index"})
    finally:
        client.close()


if __name__ == "__main__":
    main()
