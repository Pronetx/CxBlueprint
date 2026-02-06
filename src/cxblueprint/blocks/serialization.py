"""
AWS Connect Parameter Serialization Helpers

AWS Connect JSON API requires all parameter values to be strings, even for booleans
and integers. These helpers centralize the conversion logic to reduce boilerplate
and errors in block implementations.
"""

from typing import Any, Dict, Optional, Callable


def to_aws_bool(value: bool) -> str:
    """
    Convert Python bool to AWS string representation.

    Args:
        value: Python boolean

    Returns:
        "True" or "False" string

    Example:
        >>> to_aws_bool(True)
        "True"
        >>> to_aws_bool(False)
        "False"
    """
    return "True" if value else "False"


def from_aws_bool(value: str, default: bool = False) -> bool:
    """
    Parse AWS string boolean to Python bool.

    Args:
        value: AWS string boolean ("True" or "False")
        default: Default value if parsing fails

    Returns:
        Python boolean

    Example:
        >>> from_aws_bool("True")
        True
        >>> from_aws_bool("False")
        False
        >>> from_aws_bool("", default=True)
        True
    """
    if not value:
        return default
    return value == "True"


def to_aws_int(value: int) -> str:
    """
    Convert Python int to AWS string representation.

    Args:
        value: Python integer

    Returns:
        String representation of integer

    Example:
        >>> to_aws_int(5)
        "5"
        >>> to_aws_int(900)
        "900"
    """
    return str(value)


def from_aws_int(value: str, default: int = 0) -> int:
    """
    Parse AWS string integer to Python int.

    Args:
        value: AWS string integer
        default: Default value if parsing fails

    Returns:
        Python integer

    Example:
        >>> from_aws_int("5")
        5
        >>> from_aws_int("900")
        900
        >>> from_aws_int("", default=10)
        10
    """
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def serialize_optional(
    key: str, value: Optional[Any], converter: Optional[Callable[[Any], str]] = None
) -> Dict[str, str]:
    """
    Serialize optional parameter only if not None.

    Args:
        key: Parameter name
        value: Parameter value (or None)
        converter: Optional conversion function (e.g., to_aws_bool, to_aws_int)

    Returns:
        Dictionary with key-value pair if value is not None, empty dict otherwise

    Example:
        >>> serialize_optional("Timeout", 5, to_aws_int)
        {"Timeout": "5"}
        >>> serialize_optional("Timeout", None, to_aws_int)
        {}
        >>> serialize_optional("Name", "test")
        {"Name": "test"}
    """
    if value is None:
        return {}

    if converter:
        return {key: converter(value)}
    return {key: str(value)}


def build_parameters(**kwargs) -> Dict[str, str]:
    """
    Build AWS parameter dict from keyword arguments, filtering out None values.

    Args:
        **kwargs: Parameter name-value pairs

    Returns:
        Dictionary with string values, None values omitted

    Example:
        >>> build_parameters(Text="Hello", Timeout=5, OptionalParam=None)
        {"Text": "Hello", "Timeout": "5"}
    """
    return {k: str(v) for k, v in kwargs.items() if v is not None}
