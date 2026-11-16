from dataclasses import dataclass

from session import AgentSession


@dataclass(frozen=True)
class ToolContext:
    customer_id: str | None = None
    account_status: str | None = None


def build_tool_context(session: AgentSession) -> ToolContext:
    customer = session.case_facts.customer
    if not customer:
        return ToolContext()

    return ToolContext(customer_id=customer["customer_id"], account_status=customer["account_status"])
