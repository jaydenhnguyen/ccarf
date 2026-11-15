from dataclasses import dataclass

from session import AgentSession


@dataclass(frozen=True)
class ToolContext:
    customer_id: str | None = None


def build_tool_context(session: AgentSession) -> ToolContext:
    customer = session.verified_customer
    return ToolContext(customer_id=customer["customer_id"] if customer else None)
