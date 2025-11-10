git """Devin API client for session management."""
import httpx
import logging
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class DevinClient:
    """Client for interacting with Devin API."""

    def __init__(self):
        """Initialize Devin API client."""
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
    ) -> Optional[str]:
        """
        Create a new Devin session.

        Args:
            prompt: Task description for Devin
            idempotent: If True, prevents duplicate session creation

        Returns:
            Session ID if successful, None otherwise
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

            if session_id:
                logger.info(f"Devin session created: {session_id}")
            else:
                logger.warning("Devin session created but no session_id in response")

            return session_id

        except httpx.HTTPStatusError as e:
            logger.error(f"Devin API HTTP error: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Devin API request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating Devin session: {e}")
            return None

    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session status and details.

        Args:
            session_id: Devin session ID

        Returns:
            Session details dict if successful, None otherwise
        """
        try:
            response = await self.client.get(f"/sessions/{session_id}")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Devin API HTTP error for session {session_id}: "
                f"{e.response.status_code} - {e.response.text}"
            )
            return None
        except httpx.RequestError as e:
            logger.error(f"Devin API request error for session {session_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting session status: {e}")
            return None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
