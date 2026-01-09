from dataclasses import dataclass
import uuid
from .base import FlowBlock


@dataclass
class MessageParticipant(FlowBlock):
    """Play prompt / message block."""
    text: str = "Default text"

    def __post_init__(self):
        self.type = "MessageParticipant"
        if self.text and "Text" not in self.parameters:
            self.parameters["Text"] = self.text

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["Parameters"] = {"Text": self.text}
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'MessageParticipant':
        params = data.get("Parameters", {})
        return cls(
            identifier=data.get("Identifier", str(uuid.uuid4())),
            text=params.get("Text", ""),
            transitions=data.get("Transitions", {})
        )
