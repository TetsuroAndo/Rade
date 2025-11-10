"""Unit tests for core exceptions."""
import pytest
from app.core.exceptions import (
    RadeException,
    ConfigurationError,
    SecurityError,
    DevinAPIError,
    GitHubAPIError,
    RepositoryError,
    WebhookProcessingError,
    SessionNotFoundError,
)


class TestRadeException:
    """Tests for RadeException base class."""

    def test_base_exception(self):
        """Test basic exception creation."""
        exc = RadeException("Test message")
        assert str(exc) == "Test message"
        assert exc.message == "Test message"
        assert exc.details is None

    def test_exception_with_details(self):
        """Test exception with details."""
        exc = RadeException("Test message", details="Some details")
        assert exc.message == "Test message"
        assert exc.details == "Some details"


class TestDevinAPIError:
    """Tests for DevinAPIError."""

    def test_basic_error(self):
        """Test basic DevinAPIError."""
        exc = DevinAPIError("API error")
        assert exc.message == "API error"
        assert exc.status_code is None
        assert exc.response_body is None

    def test_error_with_status_code(self):
        """Test DevinAPIError with status code."""
        exc = DevinAPIError("API error", status_code=404)
        assert exc.status_code == 404
        assert "Status: 404" in exc.details

    def test_error_with_response_body(self):
        """Test DevinAPIError with response body."""
        exc = DevinAPIError("API error", status_code=500, response_body="Error details")
        assert exc.status_code == 500
        assert exc.response_body == "Error details"
        assert "Status: 500" in exc.details
        assert "Error details" in exc.details


class TestGitHubAPIError:
    """Tests for GitHubAPIError."""

    def test_basic_error(self):
        """Test basic GitHubAPIError."""
        exc = GitHubAPIError("API error")
        assert exc.message == "API error"
        assert exc.status_code is None

    def test_error_with_status_code(self):
        """Test GitHubAPIError with status code."""
        exc = GitHubAPIError("API error", status_code=403)
        assert exc.status_code == 403


class TestOtherExceptions:
    """Tests for other exception types."""

    def test_configuration_error(self):
        """Test ConfigurationError."""
        exc = ConfigurationError("Config error")
        assert isinstance(exc, RadeException)
        assert exc.message == "Config error"

    def test_security_error(self):
        """Test SecurityError."""
        exc = SecurityError("Security error")
        assert isinstance(exc, RadeException)
        assert exc.message == "Security error"

    def test_repository_error(self):
        """Test RepositoryError."""
        exc = RepositoryError("Repository error")
        assert isinstance(exc, RadeException)
        assert exc.message == "Repository error"

    def test_webhook_processing_error(self):
        """Test WebhookProcessingError."""
        exc = WebhookProcessingError("Webhook error")
        assert isinstance(exc, RadeException)
        assert exc.message == "Webhook error"

    def test_session_not_found_error(self):
        """Test SessionNotFoundError."""
        exc = SessionNotFoundError("Session not found")
        assert isinstance(exc, RadeException)
        assert exc.message == "Session not found"
