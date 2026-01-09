from dataclasses import dataclass
import uuid
from .base import FlowBlock


@dataclass
class DisconnectParticipant(FlowBlock):
    """Disconnect/hangup block."""
    
    def __post_init__(self):
        self.type = "DisconnectParticipant"

    @classmethod
    def from_dict(cls, data: dict) -> 'DisconnectParticipant':
        return cls(
            identifier=data.get("Identifier", str(uuid.uuid4())),
            parameters=data.get("Parameters", {}),
            transitions=data.get("Transitions", {})
        )
