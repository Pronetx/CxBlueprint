from dataclasses import dataclass
from typing import List, Dict, Any
import uuid
from .base import FlowBlock


@dataclass
class MessageParticipantIteratively(FlowBlock):
    """Play multiple messages in sequence."""
    messages: List[Dict[str, Any]] = None

    def __post_init__(self):
        self.type = "MessageParticipantIteratively"
        if self.messages and "Messages" not in self.parameters:
            self.parameters["Messages"] = self.messages

    def to_dict(self) -> dict:
        data = super().to_dict()
        if self.messages:
            data["Parameters"]["Messages"] = self.messages
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'MessageParticipantIteratively':
        params = data.get("Parameters", {})
        return cls(
            identifier=data.get("Identifier", str(uuid.uuid4())),
            messages=params.get("Messages", []),
            transitions=data.get("Transitions", {})
        )
