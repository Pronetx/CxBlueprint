from dataclasses import dataclass
import uuid
from .base import FlowBlock


@dataclass
class UpdateContactEventHooks(FlowBlock):
    """Update contact event hooks."""
    
    def __post_init__(self):
        self.type = "UpdateContactEventHooks"

    @classmethod
    def from_dict(cls, data: dict) -> 'UpdateContactEventHooks':
        params = data.get("Parameters", {})
        return cls(
            identifier=data.get("Identifier", str(uuid.uuid4())),
            parameters=params,
            transitions=data.get("Transitions", {})
        )
