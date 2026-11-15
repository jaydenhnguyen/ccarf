from data import ORDERS, REFUNDS_LOG
from helpers.tool_helpers import Description, RetryPolicy, ToolResult, tool_description_template

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
            returns_empty="is_refunded=false - the refund was rejected (order not found, not delivered, or amount "
            "exceeds the total); message says why. Nothing was refunded - never tell the customer it "
            "succeeded.",
            input="refund_amount must be > 0 and <= the order total.",
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
        return {
            "is_error": False,
            "content": {
                "is_refunded": False,
                "message": f"Order {order_id} not found. Cannot process refund.",
            },
        }

    if order.get("status") != "delivered":
        return {
            "is_error": False,
            "content": {
                "is_refunded": False,
                "message": f"Order {order_id} has status '{order['status']}'. Refunds can only be processed for "
                f"delivered orders.",
            },
        }

    if refund_amount > order["total"]:
        return {
            "is_error": False,
            "content": {
                "is_refunded": False,
                "message": f"Refund amount ${refund_amount:.2f} exceeds order total ${order['total']:.2f}.",
            },
        }

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
