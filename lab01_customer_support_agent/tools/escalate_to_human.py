from context import ToolContext
from core.tools.description import Description, tool_description_template
from core.tools.results import ToolResult
from core.tools.retry import RetryPolicy
from data import ESCALATIONS_LOG

escalate_to_human_schema = {
    "name": "escalate_to_human",
    "description": tool_description_template(
        Description(
            intro="Hand the case to a human agent. The human will NOT see this conversation, so the summary must be "
            "self-contained.",
            when_to_use="(1) The customer explicitly asks for a human - escalate right away, do not investigate first; "
            "(2) the request is outside policy (e.g. a refund > $500); (3) no progress after 2 attempts; "
            "(4) suspected fraud.",
            when_to_not_use="The customer is merely frustrated but the issue is simple - offer to resolve it first and "
            "escalate only if they ask again. Do not escalate a refund you are allowed to process.",
            returns_success="is_escalated=true plus escalation_id and status='pending_review'. Give the customer the "
            "escalation ID.",
            input="summary must include customer ID, order ID(s), amounts, what the customer wants, what was already "
            "tried, and the current state.",
            example='{"customer_id": "CUST-1002", "reason": "policy_gap", "summary": "Verified customer requests a '
            '$649.99 refund for ORD-5503 (4K monitor, delivered 2025-01-25). Exceeds the $500 limit.", '
            '"recommended_action": "Approve full refund once the return is received."}',
        )
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {
                "type": "string",
                "pattern": "^CUST-\\d{4}$",
                "description": "Customer ID, e.g. 'CUST-1001'.",
            },
            "reason": {
                "type": "string",
                "enum": ["customer_request", "policy_gap", "repeated_failure", "fraud"],
                "description": "Why the case is escalated.",
            },
            "summary": {
                "type": "string",
                "description": "Self-contained case summary for a human who has no transcript.",
            },
            "recommended_action": {
                "type": "string",
                "description": "Optional suggested next step for the human agent.",
            },
        },
        "required": ["customer_id", "reason", "summary"],
    },
}

escalate_to_human_retry_policy: RetryPolicy = {"retry_by": "none", "max_attempts": 1}


def escalate_to_human_handler(
    _ctx: ToolContext, customer_id: str, reason: str, summary: str, recommended_action=None
) -> ToolResult:
    escalation_record = {
        "escalation_id": f"ESC-{len(ESCALATIONS_LOG) + 9001}",
        "customer_id": customer_id,
        "reason": reason,
        "summary": summary,
        "recommended_action": recommended_action,
        "status": "pending_review",
    }
    ESCALATIONS_LOG.append(escalation_record)

    return {
        "is_error": False,
        "content": {
            "is_escalated": True,
            "escalation_id": escalation_record["escalation_id"],
            "status": "pending_review",
            "message": f"Case escalated to human agent. Escalation ID: {escalation_record['escalation_id']}. A human "
            f"agent will review this case shortly.",
        },
    }
