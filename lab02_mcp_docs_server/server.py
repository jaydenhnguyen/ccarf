import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path

from dotenv import dotenv_values
from mcp.server import MCPServer
from mcp.shared.exceptions import MCPError
from mcp.types import CallToolResult, TextContent

# Server's config
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import backend  # noqa: E402

from core.tools.errors import ToolError  # noqa: E402

log = logging.getLogger("docs-server")

handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("[docs-server] %(levelname)s %(message)s"))

log.addHandler(handler)
log.setLevel(logging.INFO)
log.propagate = False

ENV_FILE = REPO_ROOT / ".env"
UNAUTHORIZED = -32001  # JSON-RPC leaves -32000..-32099 to the server; plays the role of HTTP 401

# No client authentication on stdio: the client spawned this process, so the launch is the trust boundary
# (per-request client/user auth comes with HTTP + Bearer in B4b)

# the server's own config: read from its file
SERVER_CONFIG = dotenv_values(ENV_FILE)


def _require(value: str | None, name: str, source: str) -> str:
    if not value:
        log.error("%s missing in %s; refusing to start", name, source)
        sys.exit(1)
    return value


SERVER_KEY = _require(SERVER_CONFIG.get("DOCS_SERVER_KEY"), "DOCS_SERVER_KEY", str(ENV_FILE))

# the user this process serves. stdio = one process per user: whoever spawns us (Claude Code, raw_client)
# is acting for that user and passes their token in the env. The server only forwards it; the backend validates it
USER_TOKEN = _require(os.environ.get("DOCS_USER_TOKEN"), "DOCS_USER_TOKEN", "the launch environment")

CREDENTIALS = backend.Credentials(server_key=SERVER_KEY, user_token=USER_TOKEN)

server = MCPServer("docs")


def _meta(started: float) -> dict[str, str | float]:
    return {"trace_id": str(uuid.uuid4()), "latency_ms": round((time.perf_counter() - started) * 1000, 2)}


def _error_result(error: ToolError, started: float) -> CallToolResult:
    result = error.to_result()
    payload = {"error_category": result["error_category"], "is_retryable": result["is_retryable"], **result["content"]}
    cac = CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload))], is_error=True, _meta=_meta(started)
    )
    return cac


@server.resource(
    "docs://index",
    name="docs_index",
    description=(
        "Catalog of all company documents: doc_id, title and classification "
        "(public / internal / confidential) for each one. "
        "Metadata only, no document content. "
        "Use a doc_id from here with the get_doc tool to read the full text."
    ),
    mime_type="application/json",
)
def get_docs_index() -> list[dict[str, str]]:
    try:
        return backend.get_list_doc(CREDENTIALS)  # simulate MCP Server makes HTTP request to BE

    except backend.AuthenticationError as error:
        raise MCPError(code=UNAUTHORIZED, message=f"Unauthorized: {error}") from None


@server.tool(
    description=(
        "Find company documents whose title or content matches a keyword query. "
        "Use this when you do not yet know which document answers the question. "
        'Input: a short keyword query, e.g. "refund shipping fee" or "on-call runbook". '
        "Returns: a JSON list of matches, each with doc_id, title and classification (no content). "
        "An empty list means nothing matched; try fewer or different keywords. "
        "Then call get_doc with the best doc_id to read the full text. "
        "On error, the result is JSON with error_category, is_retryable and message. Retry only if is_retryable is "
        "true; otherwise follow the message."
    )
)
def search_docs(query: str) -> CallToolResult:
    started = time.perf_counter()
    try:
        matches = backend.search_docs(CREDENTIALS, query)  # simulate MCP Server makes HTTP request to BE

    except backend.AuthenticationError as error:
        raise MCPError(code=UNAUTHORIZED, message=f"Unauthorized: {error}") from None

    except ToolError as error:
        log.info("search_docs %r -> %s error", query, error.category)
        return _error_result(error, started)

    log.info("search_docs %r -> %d match(es)", query, len(matches))
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(matches))], _meta=_meta(started))


@server.tool(
    description=(
        "Read the full text of one company document by its exact doc_id. "
        "Use this only when you already have a doc_id (from search_docs or the user); do not guess ids. "
        "On error, the result is JSON with error_category, is_retryable and message. Retry only if is_retryable is "
        "true; otherwise follow the message. "
        'Input: a doc_id in the form "DOC-" followed by digits, e.g. "DOC-101". '
        "Returns: JSON with found=true plus doc_id, title, classification, updated_at and content; or found=false "
        "when the doc_id does not exist or the user has no access to it (a real answer, not an error: do not retry "
        "the same id; use search_docs to find the right doc_id, or tell the user they may need to request access)."
    )
)
def get_doc(doc_id: str) -> CallToolResult:
    started = time.perf_counter()
    try:
        result = backend.get_doc(CREDENTIALS, doc_id)  # simulate MCP Server makes HTTP request to BE

    except backend.AuthenticationError as error:
        raise MCPError(code=UNAUTHORIZED, message=f"Unauthorized: {error}") from None

    except ToolError as error:
        log.info("get_doc %r -> %s error", doc_id, error.category)
        return _error_result(error, started)

    log.info("get_doc %r -> found=%s", doc_id, result["found"])
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(result))], _meta=_meta(started))


if __name__ == "__main__":
    log.info("starting (stdio)")
    server.run()
