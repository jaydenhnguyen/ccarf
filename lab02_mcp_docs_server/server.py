import json
import logging
import sys
import time
import uuid

import backend
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult, TextContent

log = logging.getLogger("docs-server")

handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("[docs-server] %(levelname)s %(message)s"))

log.addHandler(handler)
log.setLevel(logging.INFO)
log.propagate = False

server = MCPServer("docs")


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
    # simulate MCP Server makes HTTP request to BE
    return backend.get_list_doc()


@server.tool(
    description=(
        "Find company documents whose title or content matches a keyword query. "
        "Use this when you do not yet know which document answers the question. "
        'Input: a short keyword query, e.g. "refund shipping fee" or "on-call runbook". '
        "Returns: a JSON list of matches, each with doc_id, title and classification (no content). "
        "An empty list means nothing matched; try fewer or different keywords. "
        "Then call get_doc with the best doc_id to read the full text."
    )
)
def search_docs(query: str) -> str:
    matches = backend.search_docs(query)
    log.info("search_docs %r -> %d match(es)", query, len(matches))
    return json.dumps(matches)


@server.tool(
    description=(
        "Read the full text of one company document by its exact doc_id. "
        "Use this only when you already have a doc_id (from search_docs or the user); do not guess ids. "
        'Input: a doc_id in the form "DOC-" followed by digits, e.g. "DOC-101". '
        "Returns: JSON with doc_id, title, classification, updated_at and content."
    )
)
def get_doc(doc_id: str) -> CallToolResult:
    started = time.perf_counter()
    doc = backend.get_doc(doc_id)
    log.info("get_doc %r -> %s", doc_id, "found" if doc else "not found")

    if doc is None:
        raise ToolError(f"No document with doc_id {doc_id!r}. Use search_docs to find a valid doc_id.")

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(doc))],
        _meta={"trace_id": str(uuid.uuid4()), "latency_ms": round((time.perf_counter() - started) * 1000, 2)},
    )


if __name__ == "__main__":
    log.info("starting (stdio)")
    server.run()
