from data import ORDERS
from helpers.tool_helpers import Description, tool_description_template

lookup_order_schema = {
    "name": "lookup_order",
    "description": tool_description_template(Description(
        intro="Look up a single order by order ID. Returns items, total, status (pending/shipped/delivered), "
              "owner customer_id, and order/delivery dates.",
        when_to_use="To check order status or delivery, or to get the order total and owner before a refund "
                    "(confirm the order's customer_id matches the verified customer).",
        when_to_not_use="To look up a customer (use get_customer). Do not guess or invent an order ID - if the "
                        "customer has not given one, ask them.",
        example='{"order_id": "ORD-5501"}',
    )),
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


def lookup_order_handler(order_id: str) -> dict:
    order = ORDERS.get(order_id)
    if not order:
        return {
            "error": True,
            "errorCategory": "validation",
            "isRetryable": True,
            "message": f"No order found for ID {order_id}. Verify the order ID with the customer.",
        }
    return {
        "order_id": order["order_id"],
        "customer_id": order["customer_id"],
        "items": order["items"],
        "total": order["total"],
        "status": order["status"],
        "ordered_at": order["ordered_at"],
        "delivered_at": order["delivered_at"],
    }
