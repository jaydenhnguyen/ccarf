import os
import re

from core.tools.errors import ToolTransientError, ToolValidationError
from data import DOCS

DOC_ID_PATTERN = re.compile(r"DOC-\d+")


def _summary(doc: dict[str, str]) -> dict[str, str]:
    return {"doc_id": doc["doc_id"], "title": doc["title"], "classification": doc["classification"]}


def get_list_doc() -> list[dict[str, str]]:
    return [_summary(doc) for doc in DOCS.values()]


def search_docs(query: str) -> list[dict[str, str]]:
    words = query.lower().split()
    return [
        _summary(doc)
        for doc in DOCS.values()
        if words and all(word in f"{doc['title']} {doc['content']}".lower() for word in words)
    ]


def get_doc(doc_id: str) -> dict[str, str] | None:
    normalized = doc_id.strip().upper()
    if not DOC_ID_PATTERN.fullmatch(normalized):
        raise ToolValidationError(
            f"Invalid doc_id {doc_id!r}. Expected 'DOC-' followed by digits, e.g. 'DOC-101'.",
            doc_id=doc_id,
        )

    if os.getenv("SIMULATE_BACKEND_TIMEOUT") == "1":
        raise ToolTransientError("Docs backend timed out. The document may exist; try again.", doc_id=normalized)

    return DOCS.get(normalized)
