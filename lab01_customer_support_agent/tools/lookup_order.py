from config import SIMULATE_LOOKUP_TIMEOUT
from core.tools.description import Description, tool_description_template
from core.tools.errors import ToolTransientError
from core.tools.results import RetryPolicy, ToolResult
from data import ORDERS

lookup_order_schema = {
    "name": "lookup_order",
    "description": tool_description_template(
        Description(
            intro="Look up a single order by order ID.",
            when_to_use="To check order status or delivery, or to get the order total and owner before a refund "
            "(confirm the order's customer_id matches the verified customer).",
            when_to_not_use="To look up a customer (use get_customer). Do not guess or invent an order ID - if the "
            "customer has not given one, ask them.",
            returns_success="found=true plus order_id, customer_id (owner), items, total, status "
            "(pending/shipped/delivered), ordered_at, delivered_at.",
            returns_empty="found=false - the order does not exist. Not a failure: do not retry, ask the customer to "
            "re-check the ID.",
            returns_error="is_error - the lookup did not complete; do NOT tell the customer the order doesn't exist.",
            example='{"order_id": "ORD-5501"}',
        )
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "pattern": "^ORD-\\d{4}$",
                "description": "Order ID exactly as given by the customer, e.g. 'ORD-5501'.",
            },
        },
        "required": ["order_id"],
    },
}

lookup_order_retry_policy: RetryPolicy = {"retry_by": "code", "max_attempts": 3}


def lookup_order_handler(order_id: str) -> ToolResult:
    if SIMULATE_LOOKUP_TIMEOUT:
        raise ToolTransientError(message="Took too long for querying the DB", order_id=order_id)

    order = ORDERS.get(order_id)
    if not order:
        return {
            "is_error": False,
            "content": {
                "found": False,
                "order_id": order_id,
                "message": f"No order found for ID {order_id}. Verify the order ID with the customer.",
            },
        }

    return {
        "is_error": False,
        "content": {
            "found": True,
            "order_id": order["order_id"],
            "customer_id": order["customer_id"],
            "items": order["items"],
            "total": order["total"],
            "status": order["status"],
            "ordered_at": order["ordered_at"],
            "delivered_at": order["delivered_at"],
        },
    }
