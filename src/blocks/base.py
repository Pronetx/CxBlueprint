from dataclasses import dataclass, field
from typing import Dict, Any, TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from typing import Self
else:
    Self = object


@dataclass
class FlowBlock:
    """
    Base class for all Amazon Connect contact flow blocks.
    Contains the core components that every block shares.
    """
    identifier: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "BaseBlock"
    parameters: Dict[str, Any] = field(default_factory=dict)
    transitions: Dict[str, Any] = field(default_factory=dict)

    def then(self, next_block: 'FlowBlock') -> 'Self':
        """Set the next action for this block."""
        self.transitions["NextAction"] = next_block.identifier
        return self

    def on_error(self, error_type: str, next_block: 'FlowBlock') -> 'Self':
        """Add an error handler for this block."""
        if "Errors" not in self.transitions:
            self.transitions["Errors"] = []
        self.transitions["Errors"].append({
            "NextAction": next_block.identifier,
            "ErrorType": error_type
        })
        return self

    def to_dict(self) -> dict:
        """Serialize block to AWS Connect JSON format."""
        return {
            "Identifier": self.identifier,
            "Type": self.type,
            "Parameters": self.parameters,
            "Transitions": self.transitions
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'FlowBlock':
        """Deserialize from AWS Connect JSON format."""
        return cls(
            identifier=data.get("Identifier", str(uuid.uuid4())),
            type=data.get("Type", "BaseBlock"),
            parameters=data.get("Parameters", {}),
            transitions=data.get("Transitions", {})
        )
