from dataclasses import dataclass
from typing import Dict, Any, TYPE_CHECKING
import uuid
from .base import FlowBlock

if TYPE_CHECKING:
    from typing import Self
else:
    Self = object


@dataclass
class GetParticipantInput(FlowBlock):
    """Get DTMF or voice input from participant."""
    text: str = ""
    store_input: str = "False"
    input_time_limit_seconds: str = "5"

    def __post_init__(self):
        self.type = "GetParticipantInput"
        if not self.parameters:
            self.parameters = {}
        if self.text:
            self.parameters["Text"] = self.text
        if self.store_input:
            self.parameters["StoreInput"] = self.store_input
        if self.input_time_limit_seconds:
            self.parameters["InputTimeLimitSeconds"] = self.input_time_limit_seconds

    def when(self, value: str, next_block: FlowBlock, operator: str = "Equals") -> 'Self':
        """Add a condition: when input matches value, go to next_block."""
        if "Conditions" not in self.transitions:
            self.transitions["Conditions"] = []
        
        self.transitions["Conditions"].append({
            "NextAction": next_block.identifier,
            "Condition": {
                "Operator": operator,
                "Operands": [value]
            }
        })
        return self

    def otherwise(self, next_block: FlowBlock) -> 'Self':
        """Set the default action when no conditions match."""
        self.transitions["NextAction"] = next_block.identifier
        return self

    def to_dict(self) -> dict:
        data = super().to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'GetParticipantInput':
        params = data.get("Parameters", {})
        return cls(
            identifier=data.get("Identifier", str(uuid.uuid4())),
            text=params.get("Text", ""),
            store_input=params.get("StoreInput", "False"),
            input_time_limit_seconds=params.get("InputTimeLimitSeconds", "5"),
            parameters=params,
            transitions=data.get("Transitions", {})
        )
