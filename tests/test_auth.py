"""Tests for OSF authentication module."""

import pytest

from dvc_osf.auth import (
    format_auth_header,
    get_token,
    redact_token_in_message,
    validate_token,
)
from dvc_osf.exceptions import OSFAuthenticationError


class TestGetToken:
    """Tests for get_token function."""

    def test_get_token_from_parameter(self):
        """Test that explicit token parameter has highest priority."""
        token = get_token(token="explicit_token")
        assert token == "explicit_token"

    def test_get_token_from_parameter_overrides_env(self, monkeypatch):
        """Test that parameter overrides environment variable."""
        monkeypatch.setenv("OSF_TOKEN", "env_token")
        token = get_token(token="explicit_token")
        assert token == "explicit_token"

    def test_get_token_from_dvc_config(self):
        """Test retrieving token from DVC config."""
        dvc_config = {"token": "dvc_config_token"}
        token = get_token(dvc_config=dvc_config)
        assert token == "dvc_config_token"

    def test_get_token_from_env(self, monkeypatch):
        """Test retrieving token from environment variable."""
        monkeypatch.setenv("OSF_TOKEN", "env_token")
        token = get_token()
        assert token == "env_token"

    def test_get_token_parameter_overrides_dvc_config(self):
        """Test that parameter overrides DVC config."""
        dvc_config = {"token": "dvc_config_token"}
        token = get_token(token="explicit_token", dvc_config=dvc_config)
        assert token == "explicit_token"

    def test_get_token_dvc_config_overrides_env(self, monkeypatch):
        """Test that DVC config overrides environment variable."""
        monkeypatch.setenv("OSF_TOKEN", "env_token")
        dvc_config = {"token": "dvc_config_token"}
        token = get_token(dvc_config=dvc_config)
        assert token == "dvc_config_token"

    def test_get_token_no_token_found(self, monkeypatch):
        """Test that missing token raises OSFAuthenticationError."""
        # Make sure env var is not set
        monkeypatch.delenv("OSF_TOKEN", raising=False)

        with pytest.raises(OSFAuthenticationError, match="token not found"):
            get_token()

    def test_get_token_empty_dvc_config(self, monkeypatch):
        """Test that empty DVC config falls through to env."""
        monkeypatch.setenv("OSF_TOKEN", "env_token")
        dvc_config = {"token": ""}
        token = get_token(dvc_config=dvc_config)
        assert token == "env_token"

    def test_get_token_dvc_config_no_token_key(self, monkeypatch):
        """Test DVC config without token key falls through to env."""
        monkeypatch.setenv("OSF_TOKEN", "env_token")
        dvc_config = {"other_key": "value"}
        token = get_token(dvc_config=dvc_config)
        assert token == "env_token"

    def test_get_token_strips_whitespace(self):
        """Test that tokens are stripped of whitespace."""
        token = get_token(token="  token_with_spaces  ")
        assert token == "token_with_spaces"


class TestValidateToken:
    """Tests for validate_token function."""

    def test_validate_valid_token(self):
        """Test validating a valid token."""
        token = validate_token("valid_token_12345")
        assert token == "valid_token_12345"

    def test_validate_empty_token(self):
        """Test that empty token raises OSFAuthenticationError."""
        with pytest.raises(OSFAuthenticationError, match="Invalid token format"):
            validate_token("")

    def test_validate_none_token(self):
        """Test that None token raises OSFAuthenticationError."""
        with pytest.raises(OSFAuthenticationError, match="Invalid token format"):
            validate_token(None)  # type: ignore

    def test_validate_whitespace_only_token(self):
        """Test that whitespace-only token raises OSFAuthenticationError."""
        with pytest.raises(OSFAuthenticationError, match="Invalid token format"):
            validate_token("   ")

    def test_validate_token_strips_whitespace(self):
        """Test that validation strips whitespace."""
        token = validate_token("  token_with_spaces  ")
        assert token == "token_with_spaces"


class TestFormatAuthHeader:
    """Tests for format_auth_header function."""

    def test_format_auth_header(self):
        """Test formatting Bearer token header."""
        header = format_auth_header("test_token_12345")
        assert header == {"Authorization": "Bearer test_token_12345"}

    def test_format_auth_header_different_token(self):
        """Test formatting with different token."""
        header = format_auth_header("another_token")
        assert header == {"Authorization": "Bearer another_token"}


class TestRedactTokenInMessage:
    """Tests for redact_token_in_message function."""

    def test_redact_token_in_message(self):
        """Test redacting token from message."""
        message = "Error with token: secret_token_12345"
        redacted = redact_token_in_message(message, "secret_token_12345")
        assert "secret_token_12345" not in redacted
        assert "[REDACTED]" in redacted

    def test_redact_token_none(self):
        """Test redacting with None token."""
        message = "Error message"
        redacted = redact_token_in_message(message, None)
        assert redacted == message

    def test_redact_token_not_in_message(self):
        """Test redacting when token not in message."""
        message = "Error message"
        redacted = redact_token_in_message(message, "some_token")
        assert redacted == message

    def test_redact_multiple_occurrences(self):
        """Test redacting multiple occurrences of token."""
        message = "Token: my_token and again my_token"
        redacted = redact_token_in_message(message, "my_token")
        assert "my_token" not in redacted
        assert redacted.count("[REDACTED]") == 2
