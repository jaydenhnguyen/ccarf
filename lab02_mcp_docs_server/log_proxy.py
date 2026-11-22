"""Sits between an MCP client (Claude Code, raw_client...) and server.py and records the traffic.

    client ──stdin──▶ log_proxy.py ──▶ server.py
                          │
                          └── every JSON-RPC line, both directions → logs/mcp_traffic.jsonl

Observation only: it relays bytes unchanged and never writes anything of its own to stdout
(stdout is the protocol channel). Watch it live with: tail -f logs/mcp_traffic.jsonl
"""

import contextlib
import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import TextIO

SERVER = Path(__file__).resolve().parent / "server.py"
LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "mcp_traffic.jsonl"


class TrafficLog:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(exist_ok=True)
        self.file = path.open("a", buffering=1)  # line-buffered: each record is on disk right away
        self.lock = threading.Lock()  # two pump threads write here

    def record(self, direction: str, line: str) -> None:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            message = line.rstrip("\n")  # not JSON: keep the raw text so nothing is hidden
        entry = {"ts": datetime.now().isoformat(timespec="milliseconds"), "dir": direction, "message": message}
        with self.lock:
            self.file.write(json.dumps(entry) + "\n")


def pump(source: TextIO, sink: TextIO, log: TrafficLog, direction: str) -> None:
    for line in source:
        log.record(direction, line)
        try:
            sink.write(line)
            sink.flush()
        except BrokenPipeError:  # the other side is gone (e.g. the server refused to start)
            break


def main() -> None:
    log = TrafficLog(LOG_FILE)
    log.record("proxy", json.dumps({"event": "session start"}))

    # pass the launcher's env through unchanged (a transparent proxy): that's how DOCS_USER_TOKEN from
    # the .mcp.json "env" block reaches the server
    server = subprocess.Popen([sys.executable, str(SERVER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    log.record("proxy", json.dumps({"event": "env", "DOCS_USER_TOKEN": os.environ.get("DOCS_USER_TOKEN")}))
    replies = threading.Thread(target=pump, args=(server.stdout, sys.stdout, log, "server→client"), daemon=True)
    replies.start()

    pump(sys.stdin, server.stdin, log, "client→server")  # until the client closes stdin

    with contextlib.suppress(BrokenPipeError):  # the server may already be gone
        server.stdin.close()
    code = server.wait()
    replies.join(timeout=2)
    log.record("proxy", json.dumps({"event": "session end", "server_exit_code": code}))
    sys.exit(code)


if __name__ == "__main__":
    main()
