from dataclasses import dataclass
import uuid
from .base import FlowBlock


@dataclass
class EndFlowExecution(FlowBlock):
    """End flow execution block."""
    
    def __post_init__(self):
        self.type = "EndFlowExecution"

    @classmethod
    def from_dict(cls, data: dict) -> 'EndFlowExecution':
        return cls(
            identifier=data.get("Identifier", str(uuid.uuid4())),
            parameters=data.get("Parameters", {}),
            transitions=data.get("Transitions", {})
        )
