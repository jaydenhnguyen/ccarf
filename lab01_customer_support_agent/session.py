from dataclasses import dataclass, field

from case_fact import CaseFacts
from core.tools.session import ToolSession


@dataclass
class AgentSession(ToolSession):
    case_facts: CaseFacts = field(default_factory=CaseFacts)
