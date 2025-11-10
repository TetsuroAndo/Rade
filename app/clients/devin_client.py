import httpx
from typing import Dict, Any
from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.exceptions import DevinAPIError, ConfigurationError

logger = get_logger(__name__)


class DevinClient:
    """Client for interacting with Devin API."""

    def __init__(self):
        """Initialize Devin API client."""
        if not settings.devin_api_key:
            raise ConfigurationError("Devin API key is not configured")
        if not settings.devin_github_secret_id:
            raise ConfigurationError("Devin GitHub secret ID is not configured")

        self.api_key = settings.devin_api_key
        self.base_url = settings.devin_api_base_url
        self.github_secret_id = settings.devin_github_secret_id
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0,
        )

    async def create_session(
        self, prompt: str, idempotent: bool = False
    ) -> str:
        """
        Create a new Devin session.

        Args:
            prompt: Task description for Devin
            idempotent: If True, prevents duplicate session creation

        Returns:
            Session ID

        Raises:
            DevinAPIError: If session creation fails
        """
        try:
            payload: Dict[str, Any] = {
                "prompt": prompt,
                "secret_ids": [self.github_secret_id],
            }
            if idempotent:
                payload["idempotent"] = True

            response = await self.client.post("/sessions", json=payload)
            response.raise_for_status()
            data = response.json()
            session_id = data.get("session_id")

            if not session_id:
                error_msg = "Devin session created but no session_id in response"
                logger.error(error_msg)
                raise DevinAPIError(error_msg)

            logger.info(f"Devin session created: {session_id}")
            return session_id

        except httpx.HTTPStatusError as e:
            error_msg = f"Devin API HTTP error: {e.response.status_code}"
            logger.error(
                f"{error_msg} - {e.response.text[:200]}",
                extra={"status_code": e.response.status_code},
            )
            raise DevinAPIError(
                error_msg,
                status_code=e.response.status_code,
                response_body=e.response.text,
            )
        except httpx.RequestError as e:
            error_msg = f"Devin API request error: {e}"
            logger.error(error_msg)
            raise DevinAPIError(error_msg)
        except DevinAPIError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error creating Devin session: {e}"
            logger.error(error_msg, exc_info=True)
            raise DevinAPIError(error_msg)

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get session status and details.

        Args:
            session_id: Devin session ID

        Returns:
            Session details dict

        Raises:
            DevinAPIError: If getting session status fails
        """
        try:
            response = await self.client.get(f"/sessions/{session_id}")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            error_msg = f"Devin API HTTP error for session {session_id}: {e.response.status_code}"
            logger.error(
                f"{error_msg} - {e.response.text[:200]}",
                extra={"session_id": session_id, "status_code": e.response.status_code},
            )
            raise DevinAPIError(
                error_msg,
                status_code=e.response.status_code,
                response_body=e.response.text,
            )
        except httpx.RequestError as e:
            error_msg = f"Devin API request error for session {session_id}: {e}"
            logger.error(error_msg, extra={"session_id": session_id})
            raise DevinAPIError(error_msg)
        except DevinAPIError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error getting session status: {e}"
            logger.error(error_msg, exc_info=True, extra={"session_id": session_id})
            raise DevinAPIError(error_msg)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
