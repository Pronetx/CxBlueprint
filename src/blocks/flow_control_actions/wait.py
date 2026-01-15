"""
Wait - Wait block for pausing flow execution.
https://docs.aws.amazon.com/connect/latest/APIReference/flow-control-actions-wait.html
"""
from dataclasses import dataclass
from typing import List, Optional
import uuid
from ..base import FlowBlock


@dataclass
class Wait(FlowBlock):
    """Wait block for pausing flow execution."""
    time_limit_seconds: int = 60
    events: Optional[List[str]] = None

    def __post_init__(self):
        self.type = "Wait"
        if not self.parameters:
            self.parameters = {}
        # Convert int to string for AWS
        self.parameters["TimeLimitSeconds"] = str(self.time_limit_seconds)
        if self.events:
            self.parameters["Events"] = self.events

    def __repr__(self) -> str:
        """Return readable representation."""
        if self.events:
            return f"Wait(seconds={self.time_limit_seconds}, events={len(self.events)})"
        return f"Wait(seconds={self.time_limit_seconds})"

    def to_dict(self) -> dict:
        data = super().to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Wait':
        params = data.get("Parameters", {})

        # Parse time limit as int
        time_str = params.get("TimeLimitSeconds", "60")
        time_limit = int(time_str) if time_str else 60

        return cls(
            identifier=data.get("Identifier", str(uuid.uuid4())),
            time_limit_seconds=time_limit,
            events=params.get("Events", []),
            parameters=params,
            transitions=data.get("Transitions", {})
        )
