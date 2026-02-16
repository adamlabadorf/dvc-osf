"""Authentication handling for OSF."""

import os
from typing import Any, Dict, Optional

from .exceptions import OSFAuthenticationError


def get_token(
    token: Optional[str] = None,
    dvc_config: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Retrieve OSF authentication token from multiple sources with priority order.

    Priority order (highest to lowest):
    1. token parameter (explicit override)
    2. DVC config (dvc_config dictionary)
    3. OSF_TOKEN environment variable

    Args:
        token: Explicit token (highest priority)
        dvc_config: DVC configuration dictionary (may contain 'token' key)

    Returns:
        OSF authentication token

    Raises:
        OSFAuthenticationError: If no token found in any source
    """
    # Priority 1: Explicit parameter
    if token:
        return validate_token(token)

    # Priority 2: DVC config
    if dvc_config and "token" in dvc_config:
        token_from_config = dvc_config["token"]
        if token_from_config:
            return validate_token(token_from_config)

    # Priority 3: Environment variable (OSF_TOKEN)
    token_from_env = os.getenv("OSF_TOKEN")
    if token_from_env:
        return validate_token(token_from_env)

    # Priority 4: Alternate environment variable (OSF_ACCESS_TOKEN)
    token_from_alt_env = os.getenv("OSF_ACCESS_TOKEN")
    if token_from_alt_env:
        return validate_token(token_from_alt_env)

    # No token found in any source
    raise OSFAuthenticationError(
        "OSF authentication token not found. "
        "Please provide a token via: "
        "(1) explicit 'token' parameter, "
        "(2) DVC remote config: 'dvc remote modify <remote> token <token>', "
        "or (3) OSF_TOKEN environment variable."
    )


def validate_token(token: str) -> str:
    """
    Validate token format.

    Performs basic validation to ensure the token is a non-empty string.
    Does NOT make an API call to verify the token with OSF.

    Args:
        token: Token to validate

    Returns:
        The validated token

    Raises:
        OSFAuthenticationError: If token is invalid
    """
    if not token or not isinstance(token, str):
        raise OSFAuthenticationError(
            "Invalid token format. Token must be a non-empty string."
        )

    # Remove whitespace
    token = token.strip()

    if not token:
        raise OSFAuthenticationError(
            "Invalid token format. Token must be a non-empty string."
        )

    return token


def format_auth_header(token: str) -> Dict[str, str]:
    """
    Format authentication header for OSF API requests.

    Args:
        token: OSF personal access token

    Returns:
        Dictionary with Authorization header
    """
    return {"Authorization": f"Bearer {token}"}


def redact_token_in_message(message: str, token: Optional[str]) -> str:
    """
    Redact token from error messages or logs to prevent exposure.

    Args:
        message: Message that may contain the token
        token: Token to redact

    Returns:
        Message with token redacted
    """
    if not token:
        return message

    # Replace token with redacted placeholder
    return message.replace(token, "[REDACTED]")
