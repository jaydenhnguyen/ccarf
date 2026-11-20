from data import DOCS


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
    return DOCS.get(doc_id.strip().upper())
