"""
GetParticipantInput - Gather customer input (DTMF or text).
https://docs.aws.amazon.com/connect/latest/APIReference/participant-actions-getparticipantinput.html
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, TYPE_CHECKING
import uuid
from ..base import FlowBlock
from ..types import Media, InputValidation, InputEncryption, DTMFConfiguration
from ..serialization import (
    serialize_optional,
    build_parameters,
    to_aws_int,
    to_aws_bool,
)

if TYPE_CHECKING:
    from typing import Self
else:
    Self = object


@dataclass
class GetParticipantInput(FlowBlock):
    """
    Gather customer input with optional validation, encryption, and storage.

    For voice contacts, gathers DTMF input.
    For other channels, gathers text strings.

    Parameters are mutually exclusive for prompts: use only one of text, prompt_id, ssml, or media.
    InputValidation: PhoneNumberValidation XOR CustomValidation
    InputEncryption requires CustomValidation to be present.

    Results:
        - When StoreInput=False: Participant input returned for condition matching
        - When StoreInput=True: No run result

    Errors:
        - NoMatchingCondition: Required if StoreInput is False
        - NoMatchingError: Always required
        - InvalidPhoneNumber: If StoreInput=True and PhoneNumberValidation specified
        - InputTimeLimitExceeded: No response before InputTimeLimitSeconds

    Restrictions:
        - Voice channel only
        - Not supported in whisper flows or hold flows
    """

    # Prompt parameters (mutually exclusive)
    text: Optional[str] = None
    prompt_id: Optional[str] = None
    ssml: Optional[str] = None
    media: Optional[Media] = None

    # Required parameters
    input_time_limit_seconds: int = 5
    store_input: bool = False

    # Optional validation/encryption
    input_validation: Optional[InputValidation] = None
    input_encryption: Optional[InputEncryption] = None
    dtmf_configuration: Optional[DTMFConfiguration] = None

    def __post_init__(self):
        self.type = "GetParticipantInput"
        self._build_parameters()

    def _build_parameters(self):
        """Build parameters dict from typed attributes."""
        params = {}

        # Prompt parameters (using serialize_optional)
        params.update(serialize_optional("Text", self.text))
        params.update(serialize_optional("PromptId", self.prompt_id))
        params.update(serialize_optional("SSML", self.ssml))

        # Media parameter
        if self.media is not None:
            params["Media"] = self.media.to_dict()

        # Required parameters (using conversion helpers)
        params["InputTimeLimitSeconds"] = to_aws_int(self.input_time_limit_seconds)
        params["StoreInput"] = to_aws_bool(self.store_input)

        # Optional parameters
        if self.input_validation is not None:
            params["InputValidation"] = self.input_validation.to_dict()
        if self.input_encryption is not None:
            params["InputEncryption"] = self.input_encryption.to_dict()
        if self.dtmf_configuration is not None:
            params["DTMFConfiguration"] = self.dtmf_configuration.to_dict()

        self.parameters = params

    def when(
        self, value: str, next_block: FlowBlock, operator: str = "Equals"
    ) -> "Self":
        """Add a condition: when input matches value, go to next_block."""
        if "Conditions" not in self.transitions:
            self.transitions["Conditions"] = []

        self.transitions["Conditions"].append(
            {
                "NextAction": next_block.identifier,
                "Condition": {"Operator": operator, "Operands": [value]},
            }
        )
        return self

    def otherwise(self, next_block: FlowBlock) -> "Self":
        """Set the default action when no conditions match."""
        self.transitions["NextAction"] = next_block.identifier
        return self

    def __repr__(self) -> str:
        """Return readable representation."""
        if self.text:
            text_preview = self.text[:40] + "..." if len(self.text) > 40 else self.text
            return f"GetParticipantInput(text='{text_preview}', timeout={self.input_time_limit_seconds})"
        elif self.prompt_id:
            return f"GetParticipantInput(prompt_id='{self.prompt_id}', timeout={self.input_time_limit_seconds})"
        return f"GetParticipantInput(timeout={self.input_time_limit_seconds})"

    def to_dict(self) -> dict:
        self._build_parameters()
        return super().to_dict()

    @classmethod
    def from_dict(cls, data: dict) -> "GetParticipantInput":
        params = data.get("Parameters", {})

        # Parse nested objects
        media_data = params.get("Media")
        input_validation_data = params.get("InputValidation")
        input_encryption_data = params.get("InputEncryption")
        dtmf_config_data = params.get("DTMFConfiguration")

        # Parse timeout as int
        timeout_str = params.get("InputTimeLimitSeconds", "5")
        timeout = int(timeout_str) if timeout_str else 5

        # Parse store_input as bool
        store_str = params.get("StoreInput", "False")
        store_bool = (
            store_str == "True" if isinstance(store_str, str) else bool(store_str)
        )

        return cls(
            identifier=data.get("Identifier", str(uuid.uuid4())),
            text=params.get("Text"),
            prompt_id=params.get("PromptId"),
            ssml=params.get("SSML"),
            media=Media.from_dict(media_data) if media_data else None,
            input_time_limit_seconds=timeout,
            store_input=store_bool,
            input_validation=(
                InputValidation.from_dict(input_validation_data)
                if input_validation_data
                else None
            ),
            input_encryption=(
                InputEncryption.from_dict(input_encryption_data)
                if input_encryption_data
                else None
            ),
            dtmf_configuration=(
                DTMFConfiguration.from_dict(dtmf_config_data)
                if dtmf_config_data
                else None
            ),
            parameters=params,
            transitions=data.get("Transitions", {}),
        )
