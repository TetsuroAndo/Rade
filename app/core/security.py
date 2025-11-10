"""Security utilities for GitHub Webhook signature verification."""
import hmac
import hashlib
from typing import Optional


def verify_github_signature(
    payload_body: bytes, signature_header: Optional[str], secret: str
) -> bool:
    """
    Verify GitHub Webhook signature.

    Args:
        payload_body: Raw request body bytes
        signature_header: X-Hub-Signature-256 header value
        secret: GitHub webhook secret

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header:
        return False

    # GitHub sends signature as "sha256=<hash>"
    if not signature_header.startswith("sha256="):
        return False

    expected_signature = signature_header[7:]  # Remove "sha256=" prefix

    # Compute HMAC SHA-256 hash
    computed_hash = hmac.new(
        secret.encode("utf-8"), payload_body, hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, computed_hash)
