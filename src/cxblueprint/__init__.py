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

__all__ = [
    "Flow",
    "FlowAnalyzer",
    "FlowValidationError",
    "LexV2Bot",
    "LexBot",
    "ViewResource",
    "Media",
    "InputValidation",
    "InputEncryption",
    "DTMFConfiguration",
    "PhoneNumberValidation",
    "CustomValidation",
]
