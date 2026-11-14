from tools.escalate_to_human import escalate_to_human_schema, escalate_to_human_handler
from tools.get_customer import get_customer_schema, get_customer_handler
from tools.lookup_order import lookup_order_schema, lookup_order_handler
from tools.process_refund import process_refund_schema, process_refund_handler

ALL_TOOLS = [
    get_customer_schema,
    lookup_order_schema,
    process_refund_schema,
    escalate_to_human_schema,
]

TOOL_HANDLERS = {
    "get_customer": get_customer_handler,
    "lookup_order": lookup_order_handler,
    "process_refund": process_refund_handler,
    "escalate_to_human": escalate_to_human_handler,
}
