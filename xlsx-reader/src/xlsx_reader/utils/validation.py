"""
Parameter validation utilities for MCP tools.
Provides consistent validation for tool parameters.
"""

from typing import Any, Dict, List, Optional, Union, Set
from pathlib import Path

from ..errors import ValidationError


def validate_required_params(params: Dict[str, Any], required: Set[str]) -> None:
    """
    Validate that all required parameters are present.

    Args:
        params: Parameter dictionary
        required: Set of required parameter names

    Raises:
        ValidationError: If required parameters are missing
    """
    missing = required - set(params.keys())
    if missing:
        raise ValidationError(
            f"Missing required parameters: {', '.join(sorted(missing))}",
            hint=f"Required parameters are: {', '.join(sorted(required))}",
        )


def validate_unknown_params(params: Dict[str, Any], allowed: Set[str]) -> None:
    """
    Validate that no unknown parameters are present.

    Args:
        params: Parameter dictionary
        allowed: Set of allowed parameter names

    Raises:
        ValidationError: If unknown parameters are found
    """
    unknown = set(params.keys()) - allowed
    if unknown:
        raise ValidationError(
            f"Unknown parameters: {', '.join(sorted(unknown))}",
            hint=f"Allowed parameters are: {', '.join(sorted(allowed))}",
        )


def validate_string_param(
    value: Any,
    param_name: str,
    required: bool = True,
    min_length: int = 0,
    max_length: Optional[int] = None,
) -> Optional[str]:
    """
    Validate a string parameter.

    Args:
        value: Parameter value to validate
        param_name: Name of the parameter for error messages
        required: Whether the parameter is required
        min_length: Minimum string length
        max_length: Maximum string length

    Returns:
        Validated string value or None if not required and not provided

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        if required:
            raise ValidationError(f"Parameter '{param_name}' is required")
        return None

    if not isinstance(value, str):
        raise ValidationError(
            f"Parameter '{param_name}' must be a string, got {type(value).__name__}"
        )

    if len(value) < min_length:
        raise ValidationError(
            f"Parameter '{param_name}' must be at least {min_length} characters long"
        )

    if max_length is not None and len(value) > max_length:
        raise ValidationError(
            f"Parameter '{param_name}' cannot exceed {max_length} characters"
        )

    return value


def validate_int_param(
    value: Any,
    param_name: str,
    required: bool = True,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
    default: Optional[int] = None,
) -> Optional[int]:
    """
    Validate an integer parameter.

    Args:
        value: Parameter value to validate
        param_name: Name of the parameter for error messages
        required: Whether the parameter is required
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        default: Default value if not provided

    Returns:
        Validated integer value or default/None if not required and not provided

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        if required:
            raise ValidationError(f"Parameter '{param_name}' is required")
        return default

    if isinstance(value, bool):
        raise ValidationError(
            f"Parameter '{param_name}' must be an integer, got boolean"
        )

    if not isinstance(value, int):
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(
                f"Parameter '{param_name}' must be an integer, got {type(value).__name__}"
            )

    if min_value is not None and value < min_value:
        raise ValidationError(
            f"Parameter '{param_name}' must be at least {min_value}, got {value}"
        )

    if max_value is not None and value > max_value:
        raise ValidationError(
            f"Parameter '{param_name}' cannot exceed {max_value}, got {value}"
        )

    return value


def validate_bool_param(
    value: Any, param_name: str, required: bool = True, default: Optional[bool] = None
) -> Optional[bool]:
    """
    Validate a boolean parameter.

    Args:
        value: Parameter value to validate
        param_name: Name of the parameter for error messages
        required: Whether the parameter is required
        default: Default value if not provided

    Returns:
        Validated boolean value or default/None if not required and not provided

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        if required:
            raise ValidationError(f"Parameter '{param_name}' is required")
        return default

    if isinstance(value, bool):
        return value

    # Try to convert string representations
    if isinstance(value, str):
        lower_value = value.lower()
        if lower_value in ("true", "1", "yes", "on"):
            return True
        elif lower_value in ("false", "0", "no", "off"):
            return False

    raise ValidationError(
        f"Parameter '{param_name}' must be a boolean, got {type(value).__name__}",
        hint="Use true/false, 1/0, yes/no, or on/off",
    )


def validate_list_param(
    value: Any,
    param_name: str,
    required: bool = True,
    item_type: type = str,
    min_length: int = 0,
    max_length: Optional[int] = None,
) -> Optional[List[Any]]:
    """
    Validate a list parameter.

    Args:
        value: Parameter value to validate
        param_name: Name of the parameter for error messages
        required: Whether the parameter is required
        item_type: Expected type of list items
        min_length: Minimum list length
        max_length: Maximum list length

    Returns:
        Validated list or None if not required and not provided

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        if required:
            raise ValidationError(f"Parameter '{param_name}' is required")
        return None

    if not isinstance(value, list):
        raise ValidationError(
            f"Parameter '{param_name}' must be a list, got {type(value).__name__}"
        )

    if len(value) < min_length:
        raise ValidationError(
            f"Parameter '{param_name}' must contain at least {min_length} items"
        )

    if max_length is not None and len(value) > max_length:
        raise ValidationError(
            f"Parameter '{param_name}' cannot contain more than {max_length} items"
        )

    # Validate item types
    for i, item in enumerate(value):
        if not isinstance(item, item_type):
            raise ValidationError(
                f"Parameter '{param_name}[{i}]' must be {item_type.__name__}, "
                f"got {type(item).__name__}"
            )

    return value


def validate_choice_param(
    value: Any,
    param_name: str,
    choices: List[Any],
    required: bool = True,
    default: Any = None,
) -> Any:
    """
    Validate a parameter that must be one of specific choices.

    Args:
        value: Parameter value to validate
        param_name: Name of the parameter for error messages
        choices: List of valid choices
        required: Whether the parameter is required
        default: Default value if not provided

    Returns:
        Validated choice value or default/None if not required and not provided

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        if required:
            raise ValidationError(f"Parameter '{param_name}' is required")
        return default

    if value not in choices:
        raise ValidationError(
            f"Parameter '{param_name}' must be one of {choices}, got {value!r}",
            hint=f"Valid choices: {', '.join(map(str, choices))}",
        )

    return value


def validate_dict_param(
    value: Any,
    param_name: str,
    required: bool = True,
    required_keys: Optional[Set[str]] = None,
    allowed_keys: Optional[Set[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Validate a dictionary parameter.

    Args:
        value: Parameter value to validate
        param_name: Name of the parameter for error messages
        required: Whether the parameter is required
        required_keys: Set of required dictionary keys
        allowed_keys: Set of allowed dictionary keys

    Returns:
        Validated dictionary or None if not required and not provided

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        if required:
            raise ValidationError(f"Parameter '{param_name}' is required")
        return None

    if not isinstance(value, dict):
        raise ValidationError(
            f"Parameter '{param_name}' must be a dictionary, got {type(value).__name__}"
        )

    if required_keys:
        missing = required_keys - set(value.keys())
        if missing:
            raise ValidationError(
                f"Parameter '{param_name}' missing required keys: {', '.join(sorted(missing))}"
            )

    if allowed_keys:
        unknown = set(value.keys()) - allowed_keys
        if unknown:
            raise ValidationError(
                f"Parameter '{param_name}' contains unknown keys: {', '.join(sorted(unknown))}",
                hint=f"Allowed keys: {', '.join(sorted(allowed_keys))}",
            )

    return value
