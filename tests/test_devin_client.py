"""Unit tests for DevinClient."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import Response, Request
from app.clients.devin_client import DevinClient
from app.core.exceptions import DevinAPIError, ConfigurationError


@pytest.fixture
def mock_settings():
    """Mock settings."""
    with patch("app.clients.devin_client.settings") as mock:
        mock.devin_api_key = "test_api_key"
        mock.devin_github_secret_id = "test_secret_id"
        mock.devin_api_base_url = "https://api.devin.ai/v1"
        yield mock


@pytest.fixture
def devin_client(mock_settings):
    """Create DevinClient instance."""
    return DevinClient()


class TestDevinClientInit:
    """Tests for DevinClient initialization."""

    def test_init_success(self, mock_settings):
        """Test successful initialization."""
        client = DevinClient()
        assert client.api_key == "test_api_key"
        assert client.github_secret_id == "test_secret_id"
        assert client.base_url == "https://api.devin.ai/v1"

    def test_init_missing_api_key(self, mock_settings):
        """Test initialization with missing API key."""
        mock_settings.devin_api_key = ""
        with pytest.raises(ConfigurationError, match="Devin API key is not configured"):
            DevinClient()

    def test_init_missing_secret_id(self, mock_settings):
        """Test initialization with missing secret ID."""
        mock_settings.devin_github_secret_id = ""
        with pytest.raises(
            ConfigurationError, match="Devin GitHub secret ID is not configured"
        ):
            DevinClient()


class TestDevinClientCreateSession:
    """Tests for create_session method."""

    @pytest.mark.asyncio
    async def test_create_session_success(self, devin_client):
        """Test successful session creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"session_id": "test_session_123"}
        mock_response.raise_for_status = MagicMock()

        devin_client.client.post = AsyncMock(return_value=mock_response)

        session_id = await devin_client.create_session("test prompt")
        assert session_id == "test_session_123"
        devin_client.client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_no_session_id(self, devin_client):
        """Test session creation without session_id in response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        devin_client.client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(DevinAPIError, match="no session_id in response"):
            await devin_client.create_session("test prompt")

    @pytest.mark.asyncio
    async def test_create_session_http_error(self, devin_client):
        """Test session creation with HTTP error."""
        from httpx import HTTPStatusError

        mock_request = MagicMock(spec=Request)
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.request = mock_request

        error = HTTPStatusError("Server Error", request=mock_request, response=mock_response)
        devin_client.client.post = AsyncMock(side_effect=error)

        with pytest.raises(DevinAPIError) as exc_info:
            await devin_client.create_session("test prompt")
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_create_session_request_error(self, devin_client):
        """Test session creation with request error."""
        from httpx import RequestError

        error = RequestError("Connection error")
        devin_client.client.post = AsyncMock(side_effect=error)

        with pytest.raises(DevinAPIError, match="request error"):
            await devin_client.create_session("test prompt")

    @pytest.mark.asyncio
    async def test_create_session_with_idempotent(self, devin_client):
        """Test session creation with idempotent flag."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"session_id": "test_session_123"}
        mock_response.raise_for_status = MagicMock()

        devin_client.client.post = AsyncMock(return_value=mock_response)

        await devin_client.create_session("test prompt", idempotent=True)
        call_args = devin_client.client.post.call_args
        assert call_args[1]["json"]["idempotent"] is True


class TestDevinClientGetSessionStatus:
    """Tests for get_session_status method."""

    @pytest.mark.asyncio
    async def test_get_session_status_success(self, devin_client):
        """Test successful status retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "session_id": "test_session_123",
            "status_enum": "working",
        }
        mock_response.raise_for_status = MagicMock()

        devin_client.client.get = AsyncMock(return_value=mock_response)

        status = await devin_client.get_session_status("test_session_123")
        assert status["session_id"] == "test_session_123"
        assert status["status_enum"] == "working"

    @pytest.mark.asyncio
    async def test_get_session_status_http_error(self, devin_client):
        """Test status retrieval with HTTP error."""
        from httpx import HTTPStatusError

        mock_request = MagicMock(spec=Request)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.request = mock_request

        error = HTTPStatusError("Not Found", request=mock_request, response=mock_response)
        devin_client.client.get = AsyncMock(side_effect=error)

        with pytest.raises(DevinAPIError) as exc_info:
            await devin_client.get_session_status("test_session_123")
        assert exc_info.value.status_code == 404


class TestDevinClientClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close(self, devin_client):
        """Test closing the client."""
        devin_client.client.aclose = AsyncMock()
        await devin_client.close()
        devin_client.client.aclose.assert_called_once()
