from dataclasses import dataclass
from typing import TypedDict

from core.tools.session import ToolSession


class VerifiedCustomer(TypedDict):
    customer_id: str
    account_status: str


@dataclass
class AgentSession(ToolSession):
    verified_customer: VerifiedCustomer | None = None
