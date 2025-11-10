"""Unit tests for WebhookService."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.webhook_service import WebhookService
from app.clients.devin_client import DevinClient
from app.repositories.session_repository import SessionRepository
from app.core.exceptions import (
    WebhookProcessingError,
    DevinAPIError,
    RepositoryError,
)


@pytest.fixture
def mock_devin_client():
    """Create mock DevinClient."""
    client = MagicMock(spec=DevinClient)
    client.create_session = AsyncMock(return_value="test_session_123")
    return client


@pytest.fixture
def mock_session_repo():
    """Create mock SessionRepository."""
    repo = MagicMock(spec=SessionRepository)
    repo.add_pending_session = MagicMock()
    return repo


@pytest.fixture
def webhook_service(mock_devin_client, mock_session_repo):
    """Create WebhookService instance."""
    return WebhookService(
        devin_client=mock_devin_client, session_repo=mock_session_repo
    )


class TestWebhookServiceIsTargetEvent:
    """Tests for _is_target_event method."""

    def test_is_target_event_valid(self, webhook_service):
        """Test valid target event."""
        payload = {
            "action": "created",
            "sender": {"login": "Code-Rabbit-App"},
            "comment": {"body": "Test comment"},
        }
        assert webhook_service._is_target_event(payload) is True

    def test_is_target_event_wrong_action(self, webhook_service):
        """Test event with wrong action."""
        payload = {
            "action": "edited",
            "sender": {"login": "Code-Rabbit-App"},
            "comment": {"body": "Test comment"},
        }
        assert webhook_service._is_target_event(payload) is False

    def test_is_target_event_wrong_sender(self, webhook_service):
        """Test event with wrong sender."""
        payload = {
            "action": "created",
            "sender": {"login": "other-bot"},
            "comment": {"body": "Test comment"},
        }
        assert webhook_service._is_target_event(payload) is False

    def test_is_target_event_no_comment(self, webhook_service):
        """Test event without comment."""
        payload = {
            "action": "created",
            "sender": {"login": "Code-Rabbit-App"},
        }
        assert webhook_service._is_target_event(payload) is False


class TestWebhookServiceExtractPRInfo:
    """Tests for _extract_pr_info method."""

    def test_extract_pr_info_issue_comment(self, webhook_service):
        """Test extracting PR info from issue_comment event."""
        payload = {
            "comment": {"body": "Test comment"},
            "repository": {"full_name": "owner/repo"},
            "issue": {
                "number": 1,
                "pull_request": {"html_url": "https://github.com/owner/repo/pull/1"},
            },
        }
        pr_info = webhook_service._extract_pr_info(payload)
        assert pr_info["pr_url"] == "https://github.com/owner/repo/pull/1"
        assert pr_info["comment_body"] == "Test comment"
        assert pr_info["pr_number"] == 1
        assert pr_info["repo_full_name"] == "owner/repo"

    def test_extract_pr_info_pull_request_review_comment(self, webhook_service):
        """Test extracting PR info from pull_request_review_comment event."""
        payload = {
            "comment": {"body": "Test comment"},
            "repository": {"full_name": "owner/repo"},
            "pull_request": {
                "number": 2,
                "html_url": "https://github.com/owner/repo/pull/2",
            },
        }
        pr_info = webhook_service._extract_pr_info(payload)
        assert pr_info["pr_url"] == "https://github.com/owner/repo/pull/2"
        assert pr_info["pr_number"] == 2

    def test_extract_pr_info_missing_fields(self, webhook_service):
        """Test extracting PR info with missing fields."""
        payload = {
            "comment": {"body": "Test comment"},
            "repository": {},
        }
        pr_info = webhook_service._extract_pr_info(payload)
        assert pr_info is None


class TestWebhookServiceBuildDevinPrompt:
    """Tests for _build_devin_prompt method."""

    def test_build_devin_prompt(self, webhook_service):
        """Test building Devin prompt."""
        prompt = webhook_service._build_devin_prompt(
            "https://github.com/owner/repo/pull/1", "Fix this bug"
        )
        assert "https://github.com/owner/repo/pull/1" in prompt
        assert "Fix this bug" in prompt
        assert "pull request" in prompt.lower()


class TestWebhookServiceProcessWebhook:
    """Tests for process_webhook method."""

    @pytest.mark.asyncio
    async def test_process_webhook_success(self, webhook_service):
        """Test successful webhook processing."""
        payload = {
            "action": "created",
            "sender": {"login": "Code-Rabbit-App"},
            "comment": {"body": "Test comment"},
            "repository": {"full_name": "owner/repo"},
            "issue": {
                "number": 1,
                "pull_request": {"html_url": "https://github.com/owner/repo/pull/1"},
            },
        }

        result = await webhook_service.process_webhook(payload)
        assert result is True
        webhook_service.devin_client.create_session.assert_called_once()
        webhook_service.session_repo.add_pending_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_webhook_not_target_event(self, webhook_service):
        """Test processing non-target event."""
        payload = {
            "action": "edited",
            "sender": {"login": "Code-Rabbit-App"},
            "comment": {"body": "Test comment"},
        }

        result = await webhook_service.process_webhook(payload)
        assert result is False

    @pytest.mark.asyncio
    async def test_process_webhook_devin_error(self, webhook_service):
        """Test processing webhook with Devin API error."""
        webhook_service.devin_client.create_session = AsyncMock(
            side_effect=DevinAPIError("API error")
        )

        payload = {
            "action": "created",
            "sender": {"login": "Code-Rabbit-App"},
            "comment": {"body": "Test comment"},
            "repository": {"full_name": "owner/repo"},
            "issue": {
                "number": 1,
                "pull_request": {"html_url": "https://github.com/owner/repo/pull/1"},
            },
        }

        with pytest.raises(WebhookProcessingError):
            await webhook_service.process_webhook(payload)

    @pytest.mark.asyncio
    async def test_process_webhook_repository_error(self, webhook_service):
        """Test processing webhook with repository error."""
        webhook_service.session_repo.add_pending_session = MagicMock(
            side_effect=RepositoryError("Repository error")
        )

        payload = {
            "action": "created",
            "sender": {"login": "Code-Rabbit-App"},
            "comment": {"body": "Test comment"},
            "repository": {"full_name": "owner/repo"},
            "issue": {
                "number": 1,
                "pull_request": {"html_url": "https://github.com/owner/repo/pull/1"},
            },
        }

        with pytest.raises(WebhookProcessingError):
            await webhook_service.process_webhook(payload)
