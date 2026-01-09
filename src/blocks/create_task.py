from dataclasses import dataclass
import uuid
from .base import FlowBlock


@dataclass
class CreateTask(FlowBlock):
    """Create a task."""
    
    def __post_init__(self):
        self.type = "CreateTask"

    @classmethod
    def from_dict(cls, data: dict) -> 'CreateTask':
        params = data.get("Parameters", {})
        return cls(
            identifier=data.get("Identifier", str(uuid.uuid4())),
            parameters=params,
            transitions=data.get("Transitions", {})
        )
