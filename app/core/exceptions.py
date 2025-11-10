"""Custom exceptions for the Rade application."""
from typing import Optional


class RadeException(Exception):
    """Base exception for all Rade application exceptions."""

    def __init__(self, message: str, details: Optional[str] = None):
        """
        Initialize exception.

        Args:
            message: Human-readable error message
            details: Optional detailed error information
        """
        self.message = message
        self.details = details
        super().__init__(self.message)


class ConfigurationError(RadeException):
    """Raised when there is a configuration error."""

    pass


class SecurityError(RadeException):
    """Raised when there is a security-related error (e.g., invalid signature)."""

    pass


class DevinAPIError(RadeException):
    """Raised when there is an error communicating with Devin API."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        """
        Initialize Devin API error.

        Args:
            message: Error message
            status_code: HTTP status code if available
            response_body: Response body if available
        """
        self.status_code = status_code
        self.response_body = response_body
        details = None
        if status_code:
            details = f"Status: {status_code}"
            if response_body:
                details += f", Response: {response_body[:200]}"
        super().__init__(message, details)


class GitHubAPIError(RadeException):
    """Raised when there is an error communicating with GitHub API."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        """
        Initialize GitHub API error.

        Args:
            message: Error message
            status_code: HTTP status code if available
            response_body: Response body if available
        """
        self.status_code = status_code
        self.response_body = response_body
        details = None
        if status_code:
            details = f"Status: {status_code}"
            if response_body:
                details += f", Response: {response_body[:200]}"
        super().__init__(message, details)


class RepositoryError(RadeException):
    """Raised when there is an error accessing the repository."""

    pass


class WebhookProcessingError(RadeException):
    """Raised when there is an error processing a webhook."""

    pass


class SessionNotFoundError(RadeException):
    """Raised when a session is not found."""

    pass
