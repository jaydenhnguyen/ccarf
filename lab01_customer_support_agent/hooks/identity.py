from core.tools.errors import ToolBusinessError, ToolPermissionError
from core.tools.results import ToolResult
from session import AgentSession


def require_active_account(_tool_input: dict, session: AgentSession) -> None:
    customer = session.verified_customer
    if customer is None:
        return  # not this hook's rule - require_verified_customer reports it

    if customer["account_status"] != "active":
        raise ToolBusinessError(
            f"Refunds are not allowed for {customer['account_status']} accounts. Escalate to a human agent.",
            customer_id=customer["customer_id"],
            account_status=customer["account_status"],
            requires_escalation=True,
        )


def require_verified_customer(_tool_input: dict, session: AgentSession) -> None:
    if session.verified_customer is None:
        raise ToolPermissionError(
            "Customer is not verified. Ask for their customer ID or email and call get_customer first."
        )


def add_verified_customer_record_to_session(tool_result: ToolResult, session: AgentSession) -> None:
    content = tool_result["content"]
    if not tool_result["is_error"] and content.get("found"):
        session.verified_customer = {
            "customer_id": content["customer_id"],
            "account_status": content["account_status"],
        }
