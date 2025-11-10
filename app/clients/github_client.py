"""GitHub API client for PR management and comments."""
import httpx
from typing import Optional, Dict, Any
from app.core.logging_config import get_logger
from app.core.exceptions import GitHubAPIError

logger = get_logger(__name__)


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
            True if successful

        Raises:
            GitHubAPIError: If comment creation fails
        """
        if not self.token:
            error_msg = "GitHub token not configured"
            logger.error(error_msg)
            raise GitHubAPIError(error_msg)

        try:
            response = await self.client.post(
                f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
                json={"body": body},
            )
            response.raise_for_status()
            logger.info(
                f"Comment created on {owner}/{repo}#{issue_number}",
                extra={"owner": owner, "repo": repo, "issue_number": issue_number},
            )
            return True

        except httpx.HTTPStatusError as e:
            error_msg = f"GitHub API HTTP error creating comment: {e.response.status_code}"
            logger.error(
                f"{error_msg} - {e.response.text[:200]}",
                extra={"status_code": e.response.status_code},
            )
            raise GitHubAPIError(
                error_msg,
                status_code=e.response.status_code,
                response_body=e.response.text,
            )
        except httpx.RequestError as e:
            error_msg = f"GitHub API request error creating comment: {e}"
            logger.error(error_msg)
            raise GitHubAPIError(error_msg)
        except GitHubAPIError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error creating GitHub comment: {e}"
            logger.error(error_msg, exc_info=True)
            raise GitHubAPIError(error_msg)

    async def get_pr_info(
        self, owner: str, repo: str, pr_number: int
    ) -> Dict[str, Any]:
        """
        Get PR information.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number

        Returns:
            PR information dict

        Raises:
            GitHubAPIError: If getting PR info fails
        """
        try:
            response = await self.client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            error_msg = f"GitHub API HTTP error getting PR info: {e.response.status_code}"
            logger.error(
                f"{error_msg} - {e.response.text[:200]}",
                extra={"status_code": e.response.status_code},
            )
            raise GitHubAPIError(
                error_msg,
                status_code=e.response.status_code,
                response_body=e.response.text,
            )
        except httpx.RequestError as e:
            error_msg = f"GitHub API request error getting PR info: {e}"
            logger.error(error_msg)
            raise GitHubAPIError(error_msg)
        except GitHubAPIError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error getting PR info: {e}"
            logger.error(error_msg, exc_info=True)
            raise GitHubAPIError(error_msg)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
