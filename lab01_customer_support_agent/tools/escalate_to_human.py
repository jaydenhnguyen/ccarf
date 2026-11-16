from case_fact import ESCALATION_REASONS
from context import ToolContext
from core.agent_logger import logger
from core.tools.description import Description, tool_description_template
from core.tools.results import ToolResult
from core.tools.retry import RetryPolicy
from data import ESCALATIONS_LOG
from hooks.case_facts import add_escalation_to_case_facts

escalate_to_human_schema = {
    "name": "escalate_to_human",
    "description": tool_description_template(
        Description(
            intro="Hand the case to a human agent. The human will NOT see this conversation, so every field must be "
            "self-contained. Customer ID and verification status are added by the system - do not include them.",
            when_to_use="(1) The customer explicitly asks for a human - escalate right away, do not investigate first; "
            "(2) a tool result has requires_escalation=true (refund over $500, account not active); "
            "(3) no progress after 2 attempts; (4) suspected fraud.",
            when_to_not_use="The customer is merely frustrated but the issue is simple - resolve it first and escalate "
            "only if they ask again. Do not escalate a refund you are allowed to process.",
            returns_success="is_escalated=true plus escalation_id and status='pending_review'. Give the customer the "
            "escalation ID.",
            input="Fill every required field. Use exact values (order IDs, amounts) - never 'the order' or 'a refund'. "
            "claimed_identity only when the customer is not verified; never invent one.",
            example='{"reason": "policy_limit", "customer_request": "Full refund of $649.99 for ORD-5503 - 4K '
            'monitor has dead pixels.", "order_ids": ["ORD-5503"], "actions_taken": ["lookup_order ORD-5503: '
            'delivered, $649.99", "process_refund $649.99: blocked, over the $500 limit"], '
            '"recommended_action": "Approve the full refund once the return is received."}',
        )
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "enum": ESCALATION_REASONS,
                "description": "Why the case is escalated.",
            },
            "customer_request": {
                "type": "string",
                "description": "What the customer wants, with exact amounts and order IDs, in one or two sentences.",
            },
            "order_ids": {
                "type": "array",
                "items": {"type": "string", "pattern": "^ORD-\\d{4}$"},
                "description": "Orders involved. Empty list if none.",
            },
            "actions_taken": {
                "type": "array",
                "items": {"type": "string"},
                "description": "What you already checked or tried and the outcome of each, e.g. "
                "'lookup_order ORD-5503: delivered, $649.99'. Empty list if nothing was tried.",
            },
            "recommended_action": {
                "type": "string",
                "description": "The single next step you recommend for the human agent.",
            },
            "claimed_identity": {
                "type": "string",
                "description": "ONLY if the customer is not verified: the name, ID, or email they gave, if any.",
            },
        },
        "required": ["reason", "customer_request", "order_ids", "actions_taken", "recommended_action"],
    },
}

escalate_to_human_retry_policy: RetryPolicy = {"retry_by": "none", "max_attempts": 1}

escalate_to_human_post_hooks = [add_escalation_to_case_facts]


def escalate_to_human_handler(
    ctx: ToolContext,
    reason: str,
    customer_request: str,
    order_ids: list[str],
    actions_taken: list[str],
    recommended_action: str,
    claimed_identity: str | None = None,
) -> ToolResult:
    is_verified = ctx.customer_id is not None

    escalation_record = {
        "escalation_id": f"ESC-{len(ESCALATIONS_LOG) + 9001}",
        "status": "pending_review",
        # SYSTEM FACTS - from code, never from Claude
        "is_verified": is_verified,
        "customer_id": ctx.customer_id,
        "account_status": ctx.account_status,
        # JUDGMENT - from Claude
        "reason": reason,
        "customer_request": customer_request,
        "order_ids": order_ids,
        "actions_taken": actions_taken,
        "recommended_action": recommended_action,
        # a claim only matters when nobody is verified
        "claimed_identity": None if is_verified else claimed_identity,
    }
    ESCALATIONS_LOG.append(escalation_record)
    logger.info("\n%s", _render_handoff(escalation_record))

    return {
        "is_error": False,
        "content": {
            "is_escalated": True,
            "escalation_id": escalation_record["escalation_id"],
            "status": "pending_review",
            "message": f"Case escalated to human agent. Escalation ID: {escalation_record['escalation_id']}. A human "
            f"agent will review this case shortly.",
            "escalation_type": reason,
        },
    }


# what the human agent reads - no transcript, only this
def _render_handoff(record: dict) -> str:
    if record["is_verified"]:
        identity = f"{record['customer_id']} ({record['account_status']})"
    else:
        identity = f"UNVERIFIED - claims: {record['claimed_identity'] or 'nothing given'}"

    actions = [f"  - {action}" for action in record["actions_taken"]] or ["  - nothing"]

    return "\n".join(
        [
            f"=== HANDOFF {record['escalation_id']} · {record['reason']} ===",
            f"Customer : {identity}",
            f"Wants    : {record['customer_request']}",
            f"Orders   : {', '.join(record['order_ids']) or '-'}",
            "Tried    :",
            *actions,
            f"Next step: {record['recommended_action']}",
        ]
    )
