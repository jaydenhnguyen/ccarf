import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from core.tools.errors import ToolTransientError, ToolValidationError
from data import DOCS, REGISTERED_SERVERS, USER_TOKENS

log = logging.getLogger("docs-server.backend")

# the backend's own config file; read per call so a flag change applies without a restart
CONFIG_FILE = Path(__file__).resolve().parent.parent / ".env"

DOC_ID_PATTERN = re.compile(r"DOC-\d+")

CLASSIFICATION_LEVEL = {"public": 0, "internal": 1, "confidential": 2}
ROLE_CLEARANCE = {"contractor": 0, "employee": 1, "hr": 2}


class AuthenticationError(Exception):
    # NOT a ToolError: a bad credential is the caller's problem (401), not something the model can fix,
    # so the server turns it into a protocol error instead of an isError result
    pass


@dataclass(frozen=True)
class Credentials:
    server_key: str
    user_token: str


@dataclass(frozen=True)
class User:
    user_id: str
    role: str


def _authenticate(creds: Credentials) -> User:
    # 1. server identity: only registered servers may call the backend
    if creds.server_key not in REGISTERED_SERVERS:
        log.warning("auth denied: unregistered server")
        raise AuthenticationError("Not authenticated. Contact your administrator.")

    # 2. delegated identity: the role is looked up from the token, never taken from the caller
    record = USER_TOKENS.get(creds.user_token)
    if record is None:
        log.warning("auth denied: unknown user token (server=%s)", REGISTERED_SERVERS[creds.server_key])
        raise AuthenticationError("Not authenticated. Contact your administrator.")
    return User(user_id=record["user_id"], role=record["role"])


def _can_read(user: User, doc: dict[str, str]) -> bool:
    return CLASSIFICATION_LEVEL[doc["classification"]] <= ROLE_CLEARANCE.get(user.role, -1)


def _visible_docs(user: User) -> list[dict[str, str]]:
    # the single filter every read path goes through, so index, search and get_doc can't disagree
    return [doc for doc in DOCS.values() if _can_read(user, doc)]


def _summary(doc: dict[str, str]) -> dict[str, str]:
    return {"doc_id": doc["doc_id"], "title": doc["title"], "classification": doc["classification"]}


def get_list_doc(creds: Credentials) -> list[dict[str, str]]:
    user = _authenticate(creds)
    return [_summary(doc) for doc in _visible_docs(user)]


def search_docs(creds: Credentials, query: str) -> list[dict[str, str]]:
    user = _authenticate(creds)
    words = query.lower().split()
    return [
        _summary(doc)
        for doc in _visible_docs(user)
        if words and all(word in f"{doc['title']} {doc['content']}".lower() for word in words)
    ]


def get_doc(creds: Credentials, doc_id: str) -> dict[str, Any]:
    user = _authenticate(creds)
    normalized = doc_id.strip().upper()
    if not DOC_ID_PATTERN.fullmatch(normalized):
        raise ToolValidationError(
            f"Invalid doc_id {doc_id!r}. Expected 'DOC-' followed by digits, e.g. 'DOC-101'.",
            doc_id=doc_id,
        )

    if dotenv_values(CONFIG_FILE).get("SIMULATE_BACKEND_TIMEOUT") == "1":
        raise ToolTransientError("Docs backend timed out. The document may exist; try again.", doc_id=normalized)

    doc = DOCS.get(normalized)
    if doc is not None and not _can_read(user, doc):
        log.warning("access denied: user=%s role=%s doc=%s", user.user_id, user.role, normalized)
        doc = None  # hidden = missing, so the caller can't probe which ids exist

    if doc is None:
        # a valid empty result, not an error. Neutral wording: the backend doesn't know any MCP tool names
        return {"found": False, "doc_id": normalized, "message": "No document with this doc_id."}
    return {"found": True, **doc}
