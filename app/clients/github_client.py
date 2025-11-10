"""GitHub API client for PR management and comments."""
import httpx
import logging
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class GitHubClient:
    """Client for interacting with GitHub API."""

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize GitHub API client.

        Args:
            github_token: GitHub Personal Access Token or GitHub App token.
                         If None, will be read from environment.
        """
        # Note: GitHub token should be passed from settings or injected
        # For now, we'll need to add it to settings if needed
        self.token = github_token
        self.base_url = "https://api.github.com"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Rade/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=30.0,
        )

    async def create_comment(
        self, owner: str, repo: str, issue_number: int, body: str
    ) -> bool:
        """
        Create a comment on an issue or PR.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue/PR number
            body: Comment body

        Returns:
            True if successful, False otherwise
        """
        if not self.token:
            logger.error("GitHub token not configured")
            return False

        try:
            response = await self.client.post(
                f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
                json={"body": body},
            )
            response.raise_for_status()
            logger.info(f"Comment created on {owner}/{repo}#{issue_number}")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(
                f"GitHub API HTTP error creating comment: "
                f"{e.response.status_code} - {e.response.text}"
            )
            return False
        except httpx.RequestError as e:
            logger.error(f"GitHub API request error creating comment: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating GitHub comment: {e}")
            return False

    async def get_pr_info(
        self, owner: str, repo: str, pr_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get PR information.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number

        Returns:
            PR information dict if successful, None otherwise
        """
        try:
            response = await self.client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"GitHub API HTTP error getting PR info: "
                f"{e.response.status_code} - {e.response.text}"
            )
            return None
        except httpx.RequestError as e:
            logger.error(f"GitHub API request error getting PR info: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting PR info: {e}")
            return None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
