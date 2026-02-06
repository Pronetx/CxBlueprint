"""
DistributeByPercentage - Distribute contacts by percentage for A/B testing.
https://docs.aws.amazon.com/connect/latest/APIReference/flow-control-actions-distributebypercentage.html

AWS Spec: Parameters must be empty {}. The block generates a random number
1-100. ALL percentage buckets must be explicit NumberLessThan conditions.
The Errors array must include NoMatchingCondition.
"""

from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING
import uuid
from ..base import FlowBlock

if TYPE_CHECKING:
    from typing import Self
else:
    Self = object


@dataclass
class DistributeByPercentage(FlowBlock):
    """Distribute contacts by percentage for A/B testing.

    Example:
        split = flow.distribute_by_percentage([50, 50])
        split.branch(0, path_a).branch(1, path_b)

        # 3-way split:
        split = flow.distribute_by_percentage([30, 40, 30])
        split.branch(0, path_a).branch(1, path_b).branch(2, path_c)
    """

    percentages: Optional[List[int]] = None

    def __post_init__(self):
        self.type = "DistributeByPercentage"
        # AWS spec: Parameters must always be empty
        self.parameters = {}

    def branch(self, index: int, next_block: "FlowBlock") -> "Self":
        """Wire the Nth percentage bucket to a block.

        Automatically calculates the cumulative NumberLessThan threshold.
        Call branch() for ALL indices 0 through N-1. Do NOT use otherwise().

        Args:
            index: Zero-based index into the percentages list.
            next_block: Block to route to for this percentage bucket.
        """
        if not self.percentages:
            raise ValueError("percentages must be set before calling branch()")
        if index < 0 or index >= len(self.percentages):
            raise ValueError(
                f"index {index} out of range for {len(self.percentages)} percentages"
            )
        cumulative = sum(self.percentages[: index + 1])
        return self.when(str(cumulative + 1), next_block, operator="NumberLessThan")

    def to_dict(self) -> dict:
        """Serialize block, auto-adding NoMatchingCondition error if missing."""
        if "Errors" not in self.transitions:
            self.transitions["Errors"] = []
        error_types = [e["ErrorType"] for e in self.transitions["Errors"]]
        if "NoMatchingCondition" not in error_types:
            self.transitions["Errors"].append(
                {"NextAction": "", "ErrorType": "NoMatchingCondition"}
            )
        return super().to_dict()

    def build_condition_metadata(self) -> tuple:
        """Build conditionMetadata and conditions for ActionMetadata.

        Returns (conditions_list, condition_metadata_list) matching
        the AWS Connect metadata format.
        """
        if not self.percentages:
            return [], []

        conditions = []
        condition_metadata = []
        for i, pct in enumerate(self.percentages):
            name = chr(65 + i)  # A, B, C, ...
            conditions.append(
                {"Condition": {"Operands": [{"displayName": name}]}}
            )
            condition_metadata.append({
                "id": str(uuid.uuid4()),
                "percent": {"value": pct, "display": f"{pct}%"},
                "name": name,
                "value": str(pct),
            })
        return conditions, condition_metadata

    def __repr__(self) -> str:
        if self.percentages:
            return f"DistributeByPercentage(percentages={self.percentages})"
        return "DistributeByPercentage()"

    @classmethod
    def from_dict(cls, data: dict) -> "DistributeByPercentage":
        return cls(
            identifier=data.get("Identifier", str(uuid.uuid4())),
            transitions=data.get("Transitions", {}),
        )
