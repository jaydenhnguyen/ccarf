DOCS = {
    "DOC-101": {
        "doc_id": "DOC-101",
        "title": "Refund policy 2026",
        "classification": "public",
        "updated_at": "2026-10-01",
        "content": (
            "Customers can request a refund within 30 days of delivery. "
            "Refunds over $500 require approval from a human agent. "
            "Shipping fees are refunded only when the order arrived more than 3 days late."
        ),
    },
    "DOC-102": {
        "doc_id": "DOC-102",
        "title": "Shipping process",
        "classification": "internal",
        "updated_at": "2026-09-12",
        "content": (
            "Orders ship within 2 business days. Standard delivery takes 3-5 days. "
            "A delivery is 'late' when it arrives after the promised date shown at checkout."
        ),
    },
    "DOC-103": {
        "doc_id": "DOC-103",
        "title": "On-call runbook: refund service",
        "classification": "internal",
        "updated_at": "2026-11-02",
        "content": (
            "If refunds fail after a deploy, check that pending DB migrations ran in prod. "
            "Roll back with `deploy rollback refund` if the error rate stays above 5% for 10 minutes."
        ),
    },
    "DOC-104": {
        "doc_id": "DOC-104",
        "title": "Salary bands 2026",
        "classification": "confidential",
        "updated_at": "2026-01-15",
        "content": "Engineer L3: $120k-$145k. Engineer L4: $150k-$180k. Engineer L5: $185k-$230k.",
    },
}

# MCP servers allowed to call this backend
REGISTERED_SERVERS = {
    "srv-key-docs-mcp-01": "docs-mcp",
}

USER_TOKENS = {
    "tok-carl": {"user_id": "u-carl", "name": "Carl", "role": "contractor"},
    "tok-alice": {"user_id": "u-alice", "name": "Alice", "role": "employee"},
    "tok-hana": {"user_id": "u-hana", "name": "Hana", "role": "hr"},
}
