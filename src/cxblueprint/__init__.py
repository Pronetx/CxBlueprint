"""CxBlueprint - Python DSL for Amazon Connect contact flow generation"""

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "0.0.0.dev0"

from .flow_builder import Flow
from .flow_analyzer import FlowAnalyzer, FlowValidationError
from .blocks.types import (
    LexV2Bot,
    LexBot,
    ViewResource,
    Media,
    InputValidation,
    InputEncryption,
    DTMFConfiguration,
    PhoneNumberValidation,
    CustomValidation,
)
from .blocks.contact_actions import TransferContactToQueue, CreateTask
from .blocks.flow_control_actions import Compare, Wait, DistributeByPercentage
from .blocks.interactions import CreateCallbackContact

__all__ = [
    "Flow",
    "FlowAnalyzer",
    "FlowValidationError",
    # Types
    "LexV2Bot",
    "LexBot",
    "ViewResource",
    "Media",
    "InputValidation",
    "InputEncryption",
    "DTMFConfiguration",
    "PhoneNumberValidation",
    "CustomValidation",
    # Common blocks (for flow.add())
    "TransferContactToQueue",
    "CreateTask",
    "Compare",
    "Wait",
    "DistributeByPercentage",
    "CreateCallbackContact",
]
