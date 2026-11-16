from config import SIMULATE_LOOKUP_TIMEOUT
from context import ToolContext
from core.tools.description import Description, tool_description_template
from core.tools.errors import ToolTransientError
from core.tools.results import ToolResult
from core.tools.retry import RetryPolicy
from data import ORDERS
from hooks.case_facts import add_found_order_to_case_facts
from hooks.identity import require_verified_customer

lookup_order_schema = {
    "name": "lookup_order",
    "description": tool_description_template(
        Description(
            intro="Look up a single order by order ID.",
            when_to_use="To check order status or delivery, or to get the order total before a refund. "
            "Requires a verified customer - call get_customer first.",
            when_to_not_use="To look up a customer (use get_customer). Do not guess or invent an order ID - if the "
            "customer has not given one, ask them.",
            returns_success="found=true plus order_id, customer_id (owner), items, total, status "
            "(pending/shipped/delivered), ordered_at, delivered_at.",
            returns_empty="found=false - the order does not exist or does not belong to the verified customer. "
            "Not a failure: do not retry; ask the customer to re-check the ID. "
            "Never guess or reveal who owns an order.",
            returns_error="is_error - permission: no verified customer; call get_customer first. "
            "transient: the lookup did not complete; do NOT tell the customer the order doesn't exist.",
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

lookup_order_pre_hooks = [require_verified_customer]
lookup_order_post_hooks = [add_found_order_to_case_facts]


def lookup_order_handler(_ctx: ToolContext, order_id: str) -> ToolResult:
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

    if order["customer_id"] != _ctx.customer_id:
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
