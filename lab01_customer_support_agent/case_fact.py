from dataclasses import asdict, dataclass, field
from typing import Literal, NotRequired, TypedDict, get_args

from core.case_fact import render_facts_block

type EscalationReason = Literal["customer_request", "policy_limit", "account_issue", "repeated_failure", "fraud"]

ESCALATION_REASONS = list(get_args(EscalationReason.__value__))
CASE_FACTS_INSTRUCTION = (
    "The system recorded these facts from tool results in this conversation. They are authoritative: "
    "if anything earlier in the conversation conflicts with them, trust these."
)


class CustomerFact(TypedDict):
    customer_id: str
    account_status: str


class OrderFact(TypedDict):
    total: float
    status: str
    refunded: NotRequired[float]
    refund_ids: NotRequired[list[str]]
    refund_blocked: NotRequired[str]


class EscalationFact(TypedDict):
    escalation_id: str
    escalation_type: EscalationReason


@dataclass
class CaseFacts:
    customer: CustomerFact | None = None
    escalation: EscalationFact | None = None
    orders: dict[str, OrderFact] = field(default_factory=dict)


def render_case_facts(facts: CaseFacts) -> str:
    return render_facts_block(asdict(facts), tag="case_facts", instruction=CASE_FACTS_INSTRUCTION)
