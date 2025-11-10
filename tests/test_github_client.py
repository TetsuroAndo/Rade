"""Unit tests for GitHubClient."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import Response, Request
from app.clients.github_client import GitHubClient
from app.core.exceptions import GitHubAPIError


@pytest.fixture
def github_client():
    """Create GitHubClient instance with token."""
    return GitHubClient(github_token="test_token")


@pytest.fixture
def github_client_no_token():
    """Create GitHubClient instance without token."""
    return GitHubClient(github_token=None)


class TestGitHubClientInit:
    """Tests for GitHubClient initialization."""

    def test_init_with_token(self):
        """Test initialization with token."""
        client = GitHubClient(github_token="test_token")
        assert client.token == "test_token"
        assert "Authorization" in client.client.headers

    def test_init_without_token(self):
        """Test initialization without token."""
        client = GitHubClient(github_token=None)
        assert client.token is None
        assert "Authorization" not in client.client.headers


class TestGitHubClientCreateComment:
    """Tests for create_comment method."""

    @pytest.mark.asyncio
    async def test_create_comment_success(self, github_client):
        """Test successful comment creation."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        github_client.client.post = AsyncMock(return_value=mock_response)

        result = await github_client.create_comment(
            owner="test_owner", repo="test_repo", issue_number=1, body="Test comment"
        )
        assert result is True
        github_client.client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_comment_no_token(self, github_client_no_token):
        """Test comment creation without token."""
        with pytest.raises(GitHubAPIError, match="GitHub token not configured"):
            await github_client_no_token.create_comment(
                owner="test_owner",
                repo="test_repo",
                issue_number=1,
                body="Test comment",
            )

    @pytest.mark.asyncio
    async def test_create_comment_http_error(self, github_client):
        """Test comment creation with HTTP error."""
        from httpx import HTTPStatusError

        mock_request = MagicMock(spec=Request)
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.request = mock_request

        error = HTTPStatusError("Forbidden", request=mock_request, response=mock_response)
        github_client.client.post = AsyncMock(side_effect=error)

        with pytest.raises(GitHubAPIError) as exc_info:
            await github_client.create_comment(
                owner="test_owner",
                repo="test_repo",
                issue_number=1,
                body="Test comment",
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_create_comment_request_error(self, github_client):
        """Test comment creation with request error."""
        from httpx import RequestError

        error = RequestError("Connection error")
        github_client.client.post = AsyncMock(side_effect=error)

        with pytest.raises(GitHubAPIError, match="request error"):
            await github_client.create_comment(
                owner="test_owner",
                repo="test_repo",
                issue_number=1,
                body="Test comment",
            )


class TestGitHubClientGetPRInfo:
    """Tests for get_pr_info method."""

    @pytest.mark.asyncio
    async def test_get_pr_info_success(self, github_client):
        """Test successful PR info retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "number": 1,
            "title": "Test PR",
            "state": "open",
        }
        mock_response.raise_for_status = MagicMock()

        github_client.client.get = AsyncMock(return_value=mock_response)

        pr_info = await github_client.get_pr_info("test_owner", "test_repo", 1)
        assert pr_info["number"] == 1
        assert pr_info["title"] == "Test PR"

    @pytest.mark.asyncio
    async def test_get_pr_info_http_error(self, github_client):
        """Test PR info retrieval with HTTP error."""
        from httpx import HTTPStatusError

        mock_request = MagicMock(spec=Request)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.request = mock_request

        error = HTTPStatusError("Not Found", request=mock_request, response=mock_response)
        github_client.client.get = AsyncMock(side_effect=error)

        with pytest.raises(GitHubAPIError) as exc_info:
            await github_client.get_pr_info("test_owner", "test_repo", 1)
        assert exc_info.value.status_code == 404


class TestGitHubClientClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close(self, github_client):
        """Test closing the client."""
        github_client.client.aclose = AsyncMock()
        await github_client.close()
        github_client.client.aclose.assert_called_once()
