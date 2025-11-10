"""Unit tests for security module."""
from app.core.security import verify_github_signature
import hmac
import hashlib


class TestVerifyGitHubSignature:
    """Tests for GitHub signature verification."""

    def test_valid_signature(self):
        """Test valid signature verification."""
        secret = "test_secret"
        payload = b'{"test": "data"}'
        computed_hash = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        signature = f"sha256={computed_hash}"

        assert verify_github_signature(payload, signature, secret) is True

    def test_invalid_signature(self):
        """Test invalid signature verification."""
        secret = "test_secret"
        payload = b'{"test": "data"}'
        invalid_signature = "sha256=invalid_hash"

        assert verify_github_signature(payload, invalid_signature, secret) is False

    def test_missing_signature(self):
        """Test missing signature."""
        secret = "test_secret"
        payload = b'{"test": "data"}'

        assert verify_github_signature(payload, None, secret) is False

    def test_invalid_signature_format(self):
        """Test invalid signature format."""
        secret = "test_secret"
        payload = b'{"test": "data"}'
        invalid_format = "invalid_format"

        assert verify_github_signature(payload, invalid_format, secret) is False

    def test_empty_payload(self):
        """Test empty payload."""
        secret = "test_secret"
        payload = b""
        computed_hash = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        signature = f"sha256={computed_hash}"

        assert verify_github_signature(payload, signature, secret) is True

    def test_different_secrets(self):
        """Test that different secrets produce different signatures."""
        secret1 = "secret1"
        secret2 = "secret2"
        payload = b'{"test": "data"}'
        computed_hash1 = hmac.new(
            secret1.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        signature1 = f"sha256={computed_hash1}"

        assert verify_github_signature(payload, signature1, secret1) is True
        assert verify_github_signature(payload, signature1, secret2) is False
