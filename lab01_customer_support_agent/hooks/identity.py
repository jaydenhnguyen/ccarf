from core.tools.errors import ToolBusinessError, ToolPermissionError
from core.tools.results import ToolResult
from session import AgentSession


def require_active_account(_tool_input: dict, session: AgentSession) -> None:
    if not session.case_facts or not session.case_facts.customer:
        return  # not this hook's rule - require_verified_customer reports it

    customer = session.case_facts.customer

    if customer["account_status"] != "active":
        raise ToolBusinessError(
            f"Refunds are not allowed for {customer['account_status']} accounts. Escalate to a human agent.",
            customer_id=customer["customer_id"],
            account_status=customer["account_status"],
            requires_escalation=True,
        )


def require_verified_customer(_tool_input: dict, session: AgentSession) -> None:
    customer = session.case_facts.customer

    if customer is None or customer["customer_id"] is None:
        raise ToolPermissionError(
            "Customer is not verified. Ask for their customer ID or email and call get_customer first."
        )


def add_verified_customer_record_to_case_facts(tool_result: ToolResult, session: AgentSession) -> None:
    content = tool_result["content"]

    if not tool_result["is_error"] and content.get("found"):
        session.case_facts.customer = {
            "customer_id": content["customer_id"],
            "account_status": content["account_status"],
        }
