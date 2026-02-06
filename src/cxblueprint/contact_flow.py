from dataclasses import dataclass, field
from typing import Dict, List, Any
import json
from .blocks.base import FlowBlock


@dataclass
class ContactFlow:
    """Top-level contact flow containing all blocks."""

    version: str = "2019-10-30"
    start_action: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    actions: List[FlowBlock] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize entire flow to AWS Connect JSON."""
        return {
            "Version": self.version,
            "StartAction": self.start_action,
            "Metadata": self.metadata,
            "Actions": [action.to_dict() for action in self.actions],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert flow to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
