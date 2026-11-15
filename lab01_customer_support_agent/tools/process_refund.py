from core.tools.description import Description, tool_description_template
from core.tools.errors import ToolBusinessError, ToolValidationError
from core.tools.results import RetryPolicy, ToolResult
from data import ORDERS, REFUNDS_LOG

REFUND_AUTO_APPROVE_LIMIT = 500

process_refund_schema = {
    "name": "process_refund",
    "description": tool_description_template(
        Description(
            intro="Issue a refund (full or partial) for a DELIVERED order.",
            when_to_use="Only after (1) the customer is verified via get_customer and (2) the order is confirmed via "
            "lookup_order as delivered and belonging to that customer.",
            when_to_not_use="Orders that are pending or shipped; unverified customers; refunds over $500 "
            "(use escalate_to_human instead).",
            returns_success="is_refunded=true plus refund_id, order_id, amount, status='processed'.",
            returns_error="is_error - NOTHING was refunded; never tell the customer it succeeded. "
            "validation: order not found or amount exceeds the order total - fix with the customer, then call "
            "again. business: refund not allowed by policy - do NOT retry; if the message says to escalate "
            "(refunds over $500), call escalate_to_human, otherwise explain using the message.",
            input="refund_amount must be > 0 and <= the order total. Refunds over $500 are not processed here.",
            example='{"order_id": "ORD-5502", "refund_amount": 59.99, "reason": "Laptop stand arrived damaged"}',
        )
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "pattern": "^ORD-\\d{4}$",
                "description": "Order ID to refund, e.g. 'ORD-5501'.",
            },
            "refund_amount": {
                "type": "number",
                "exclusiveMinimum": 0,
                "description": "Refund amount in USD, e.g. 59.99. Can be partial.",
            },
            "reason": {
                "type": "string",
                "description": "Short reason in the customer's words, e.g. 'defective product', 'wrong item shipped'.",
            },
        },
        "required": ["order_id", "refund_amount", "reason"],
    },
}

process_refund_retry_policy: RetryPolicy = {"retry_by": "none", "max_attempts": 1}


def process_refund_handler(order_id: str, refund_amount: float, reason: str) -> ToolResult:
    order = ORDERS.get(order_id)
    if order is None:
        raise ToolValidationError(f"Order {order_id} not found. Re-check the ID with the customer.", order_id=order_id)

    if order["status"] != "delivered":
        raise ToolBusinessError(
            f"Refunds are only allowed for delivered orders; this order is '{order['status']}'.",
            order_id=order_id,
            order_status=order["status"],
        )

    if refund_amount > order["total"]:
        raise ToolValidationError(
            f"Refund amount ${refund_amount:.2f} exceeds order total ${order['total']:.2f}.",
            order_id=order_id,
            refund_amount=refund_amount,
            order_total=order["total"],
        )

    if refund_amount > REFUND_AUTO_APPROVE_LIMIT:
        raise ToolBusinessError(
            f"Refunds over ${REFUND_AUTO_APPROVE_LIMIT} need human approval. Call escalate_to_human instead.",
            order_id=order_id,
            refund_amount=refund_amount,
            limit=REFUND_AUTO_APPROVE_LIMIT,
            requires_escalation=True,
        )

    refund_record = {
        "refund_id": f"REF-{len(REFUNDS_LOG) + 7001}",
        "order_id": order_id,
        "amount": refund_amount,
        "reason": reason,
        "status": "processed",
    }
    REFUNDS_LOG.append(refund_record)

    return {
        "is_error": False,
        "content": {
            "is_refunded": True,
            "refund_id": refund_record["refund_id"],
            "order_id": order_id,
            "amount": refund_amount,
            "status": "processed",
            "message": f"Refund of ${refund_amount:.2f} processed successfully for order {order_id}.",
        },
    }
