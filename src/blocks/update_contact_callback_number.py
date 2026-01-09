from dataclasses import dataclass
import uuid
from .base import FlowBlock


@dataclass
class UpdateContactCallbackNumber(FlowBlock):
    """Update the callback number for a contact."""
    
    def __post_init__(self):
        self.type = "UpdateContactCallbackNumber"

    @classmethod
    def from_dict(cls, data: dict) -> 'UpdateContactCallbackNumber':
        params = data.get("Parameters", {})
        return cls(
            identifier=data.get("Identifier", str(uuid.uuid4())),
            parameters=params,
            transitions=data.get("Transitions", {})
        )
