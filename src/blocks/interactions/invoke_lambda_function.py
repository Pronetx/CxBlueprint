"""
InvokeLambdaFunction - Invoke AWS Lambda function.
https://docs.aws.amazon.com/connect/latest/APIReference/interactions-invokelambdafunction.html
"""
from dataclasses import dataclass
from typing import Optional
import uuid
from ..base import FlowBlock


@dataclass
class InvokeLambdaFunction(FlowBlock):
    """Invoke AWS Lambda function."""
    lambda_function_arn: str = ""
    invocation_time_limit_seconds: int = 8

    def __post_init__(self):
        self.type = "InvokeLambdaFunction"
        if not self.parameters:
            self.parameters = {}
        if self.lambda_function_arn:
            self.parameters["LambdaFunctionARN"] = self.lambda_function_arn
        # Convert int to string for AWS
        self.parameters["InvocationTimeLimitSeconds"] = str(self.invocation_time_limit_seconds)

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
    def from_dict(cls, data: dict) -> 'InvokeLambdaFunction':
        params = data.get("Parameters", {})

        # Parse timeout as int
        timeout_str = params.get("InvocationTimeLimitSeconds", "8")
        timeout = int(timeout_str) if timeout_str else 8

        return cls(
            identifier=data.get("Identifier", str(uuid.uuid4())),
            lambda_function_arn=params.get("LambdaFunctionARN", ""),
            invocation_time_limit_seconds=timeout,
            parameters=params,
            transitions=data.get("Transitions", {})
        )
