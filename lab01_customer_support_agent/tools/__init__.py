from tools.escalate_to_human import escalate_to_human_schema, escalate_to_human_handler, escalate_to_human_retry_policy
from tools.get_customer import get_customer_schema, get_customer_handler, get_customer_retry_policy
from tools.lookup_order import lookup_order_schema, lookup_order_handler, lookup_order_retry_policy
from tools.process_refund import process_refund_schema, process_refund_handler, process_refund_retry_policy

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

RETRY_POLICIES = {
    "get_customer": get_customer_retry_policy,
    "lookup_order": lookup_order_retry_policy,
    "process_refund": process_refund_retry_policy,
    "escalate_to_human": escalate_to_human_retry_policy,
}
