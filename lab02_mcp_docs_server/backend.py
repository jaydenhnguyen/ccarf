from data import DOCS


def get_list_doc() -> list[dict[str, str]]:
    return [
        {"doc_id": doc["doc_id"], "title": doc["title"], "classification": doc["classification"]}
        for doc in DOCS.values()
    ]
