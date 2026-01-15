"""
Compare - Compare/branch block for conditional logic.
https://docs.aws.amazon.com/connect/latest/APIReference/flow-control-actions-compare.html
"""

from dataclasses import dataclass
import uuid
from ..base import FlowBlock


@dataclass
class Compare(FlowBlock):
    """Compare/branch block for conditional logic."""

    comparison_value: str = ""

    def __post_init__(self):
        self.type = "Compare"
        if self.comparison_value and "ComparisonValue" not in self.parameters:
            self.parameters["ComparisonValue"] = self.comparison_value

    def __repr__(self) -> str:
        """Return readable representation."""
        if self.comparison_value:
            value_preview = (
                self.comparison_value[:30] + "..."
                if len(self.comparison_value) > 30
                else self.comparison_value
            )
            return f"Compare(value='{value_preview}')"
        return "Compare()"

    def to_dict(self) -> dict:
        data = super().to_dict()
        if self.comparison_value:
            data["Parameters"]["ComparisonValue"] = self.comparison_value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Compare":
        params = data.get("Parameters", {})
        return cls(
            identifier=data.get("Identifier", str(uuid.uuid4())),
            comparison_value=params.get("ComparisonValue", ""),
            parameters=params,
            transitions=data.get("Transitions", {}),
        )
