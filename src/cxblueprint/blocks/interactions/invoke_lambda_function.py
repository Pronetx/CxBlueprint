"""
InvokeLambdaFunction - Invoke AWS Lambda function.
https://docs.aws.amazon.com/connect/latest/APIReference/interactions-invokelambdafunction.html
"""

from dataclasses import dataclass
from typing import Optional
import uuid
from ..base import FlowBlock
from ..serialization import to_aws_int, from_aws_int, serialize_optional


@dataclass
class InvokeLambdaFunction(FlowBlock):
    """Invoke AWS Lambda function."""

    lambda_function_arn: str = ""
    invocation_time_limit_seconds: int = 8

    def __post_init__(self):
        self.type = "InvokeLambdaFunction"
        if self.invocation_time_limit_seconds > 8:
            raise ValueError(
                f"Lambda timeout cannot exceed 8 seconds (got {self.invocation_time_limit_seconds}). "
                "This is an AWS Connect limit."
            )
        if not self.parameters:
            self.parameters = {}

        # Use serialization helpers
        self.parameters.update(
            serialize_optional("LambdaFunctionARN", self.lambda_function_arn)
        )
        self.parameters["InvocationTimeLimitSeconds"] = to_aws_int(
            self.invocation_time_limit_seconds
        )

    def __repr__(self) -> str:
        """Return readable representation."""
        # Show last part of ARN for readability
        arn_display = self.lambda_function_arn
        if len(arn_display) > 40:
            arn_display = "..." + arn_display[-37:]
        return f"InvokeLambdaFunction(arn='{arn_display}', timeout={self.invocation_time_limit_seconds})"

    def to_dict(self) -> dict:
        data = super().to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "InvokeLambdaFunction":
        params = data.get("Parameters", {})

        # Parse timeout as int using helper
        timeout = from_aws_int(params.get("InvocationTimeLimitSeconds", "8"), default=8)

        return cls(
            identifier=data.get("Identifier", str(uuid.uuid4())),
            lambda_function_arn=params.get("LambdaFunctionARN", ""),
            invocation_time_limit_seconds=timeout,
            parameters=params,
            transitions=data.get("Transitions", {}),
        )
