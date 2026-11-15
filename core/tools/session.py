from dataclasses import dataclass, field


@dataclass
class ToolSession:
    """Per-conversation state the executor itself needs. Labs extend it with their own facts."""

    call_counts: dict[str, int] = field(default_factory=dict)
