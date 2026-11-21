import hmac
import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from mcp.server import MCPServer
from mcp.server.context import CallNext, HandlerResult, ServerRequestContext
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
CLIENT_TOKEN_META_KEY = "docs/client_token"
USER_TOKEN_META_KEY = "docs/user_token"
UNAUTHORIZED = -32001
HANDSHAKE_METHODS = frozenset({"initialize", "notifications/initialized"})

# the MCP server's own config
SERVER_CONFIG = dotenv_values(ENV_FILE)

# dev-only escape hatch for tools that can't send our _meta tokens (the Inspector)
DEV_SKIP_CLIENT_AUTH = SERVER_CONFIG.get("DOCS_MCP_DEV_SKIP_CLIENT_AUTH") == "1"
DEV_USER_TOKEN = SERVER_CONFIG.get("DOCS_MCP_DEV_USER_TOKEN") if DEV_SKIP_CLIENT_AUTH else None


def _require_config(name: str) -> str:
    value = SERVER_CONFIG.get(name)
    if not value:
        log.error("%s missing in %s; refusing to start", name, ENV_FILE)
        sys.exit(1)
    return value


ACCEPTED_CLIENT_TOKEN = _require_config("DOCS_MCP_ACCEPTED_CLIENT_TOKEN")
SERVER_KEY = _require_config("DOCS_SERVER_KEY")  # the server's own identity towards the backend

# who this request is for: set per request by the middleware, read by the handlers.
# a contextvar because the static docs://index resource can't receive the request Context
CURRENT_USER_TOKEN: ContextVar[str] = ContextVar("current_user_token")


# runs before EVERY message
async def authenticate_request(ctx: ServerRequestContext[Any, Any], call_next: CallNext) -> HandlerResult:
    meta = ctx.meta or {}

    if not DEV_SKIP_CLIENT_AUTH:
        presented = meta.get(CLIENT_TOKEN_META_KEY)

        if not isinstance(presented, str) or not hmac.compare_digest(presented, ACCEPTED_CLIENT_TOKEN):
            reason = "missing" if presented is None else "wrong"
            log.warning("client auth denied: method=%s token=%s", ctx.method, reason)
            raise MCPError(code=UNAUTHORIZED, message="Unauthorized: missing or invalid client token")

    # the handshake belongs to the client app (before any user logs in) and touches no user data,
    # so it needs the client token only; every other message also needs a user token
    if ctx.method in HANDSHAKE_METHODS:
        return await call_next(ctx)

    user_token = meta.get(USER_TOKEN_META_KEY) or DEV_USER_TOKEN
    if not isinstance(user_token, str) or not user_token:
        log.warning("client auth denied: method=%s user token=missing", ctx.method)
        raise MCPError(code=UNAUTHORIZED, message="Unauthorized: missing user token")

    reset = CURRENT_USER_TOKEN.set(user_token)
    try:
        return await call_next(ctx)
    finally:
        CURRENT_USER_TOKEN.reset(reset)


def _credentials() -> backend.Credentials:
    return backend.Credentials(server_key=SERVER_KEY, user_token=CURRENT_USER_TOKEN.get())


if DEV_SKIP_CLIENT_AUTH:
    log.warning("DOCS_MCP_DEV_SKIP_CLIENT_AUTH=1: client token check is OFF, dev user = %s (dev only)", DEV_USER_TOKEN)

server = MCPServer("docs", middleware=[authenticate_request])


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
        return backend.get_list_doc(_credentials())  # simulate MCP Server makes HTTP request to BE

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
        matches = backend.search_docs(_credentials(), query)  # simulate MCP Server makes HTTP request to BE

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
        "when no document has that doc_id (a real answer, not an error: do not retry the same id; "
        "use search_docs to find the right doc_id)."
    )
)
def get_doc(doc_id: str) -> CallToolResult:
    started = time.perf_counter()
    try:
        result = backend.get_doc(_credentials(), doc_id)  # simulate MCP Server makes HTTP request to BE

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
