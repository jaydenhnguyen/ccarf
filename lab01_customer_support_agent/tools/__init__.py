from tools.escalate_to_human import escalate_to_human_handler, escalate_to_human_schema
from tools.get_customer import get_customer_handler, get_customer_schema
from tools.lookup_order import lookup_order_handler, lookup_order_schema
from tools.process_refund import process_refund_handler, process_refund_schema

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
