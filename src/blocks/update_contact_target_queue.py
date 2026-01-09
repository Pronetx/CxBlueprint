from dataclasses import dataclass
import uuid
from .base import FlowBlock


@dataclass
class UpdateContactTargetQueue(FlowBlock):
    """Update the target queue for a contact."""
    
    def __post_init__(self):
        self.type = "UpdateContactTargetQueue"

    @classmethod
    def from_dict(cls, data: dict) -> 'UpdateContactTargetQueue':
        params = data.get("Parameters", {})
        return cls(
            identifier=data.get("Identifier", str(uuid.uuid4())),
            parameters=params,
            transitions=data.get("Transitions", {})
        )
