"""Webhook service for processing GitHub webhook events."""
import logging
from typing import Optional, Dict, Any
from app.clients.devin_client import DevinClient
from app.repositories.session_repository import SessionRepository
from app.core.config import settings

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for processing GitHub webhook events."""

    def __init__(
        self,
        devin_client: Optional[DevinClient] = None,
        session_repo: Optional[SessionRepository] = None,
    ):
        """
        Initialize webhook service.

        Args:
            devin_client: Devin API client instance. If None, creates a new one.
            session_repo: Session repository instance. If None, creates a new one.
        """
        self.devin_client = devin_client or DevinClient()
        self.session_repo = session_repo or SessionRepository()

    async def process_webhook(self, payload: Dict[str, Any]) -> bool:
        """
        Process GitHub webhook payload.

        Args:
            payload: GitHub webhook payload dictionary

        Returns:
            True if processed successfully, False otherwise
        """
        # 1. Check if this is a target event
        if not self._is_target_event(payload):
            logger.debug("Event is not a target event, skipping")
            return False

        # 2. Extract information from payload
        try:
            pr_info = self._extract_pr_info(payload)
            if not pr_info:
                logger.warning("Could not extract PR information from payload")
                return False

            pr_url = pr_info["pr_url"]
            comment_body = pr_info["comment_body"]
            original_pr_number = pr_info["pr_number"]
            repo_full_name = pr_info["repo_full_name"]

            logger.info(
                f"Processing webhook for PR {repo_full_name}#{original_pr_number}"
            )

        except Exception as e:
            logger.error(f"Error extracting information from payload: {e}")
            return False

        # 3. Build Devin prompt
        prompt = self._build_devin_prompt(pr_url, comment_body)

        # 4. Create Devin session
        session_id = await self.devin_client.create_session(prompt)
        if not session_id:
            logger.error("Failed to create Devin session")
            return False

        # 5. Save session to repository for monitoring
        self.session_repo.add_pending_session(
            session_id=session_id,
            original_pr_number=original_pr_number,
            repo_full_name=repo_full_name,
            comment_body=comment_body,
        )

        logger.info(
            f"Successfully created Devin session {session_id} for {repo_full_name}#{original_pr_number}"
        )
        return True

    def _is_target_event(self, payload: Dict[str, Any]) -> bool:
        """
        Check if the webhook event is a target event.

        Args:
            payload: GitHub webhook payload

        Returns:
            True if this is a target event, False otherwise
        """
        # Check event type
        event_type = payload.get("action")
        if event_type != "created":
            return False

        # Check if sender is a target bot
        sender = payload.get("sender", {})
        sender_login = sender.get("login", "")
        if sender_login not in settings.target_bot_usernames:
            logger.debug(f"Sender {sender_login} is not in target bot list")
            return False

        # Check if this is a comment event (issue_comment or pull_request_review_comment)
        # This check is done by checking if comment exists in payload
        if "comment" not in payload:
            return False

        return True

    def _extract_pr_info(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract PR information from webhook payload.

        Args:
            payload: GitHub webhook payload

        Returns:
            Dictionary with pr_url, comment_body, pr_number, repo_full_name
            or None if extraction fails
        """
        try:
            comment = payload.get("comment", {})
            comment_body = comment.get("body", "")

            repo = payload.get("repository", {})
            repo_full_name = repo.get("full_name", "")

            # Handle issue_comment event
            if "issue" in payload:
                issue = payload.get("issue", {})
                pr_number = issue.get("number")
                pr_url = issue.get("pull_request", {}).get("html_url")

                # If html_url is not in pull_request, construct it
                if not pr_url:
                    owner = repo.get("owner", {}).get("login") or repo_full_name.split("/")[0]
                    repo_name = repo.get("name") or repo_full_name.split("/")[-1]
                    pr_url = f"https://github.com/{repo_full_name}/pull/{pr_number}"

            # Handle pull_request_review_comment event
            elif "pull_request" in payload:
                pr = payload.get("pull_request", {})
                pr_number = pr.get("number")
                pr_url = pr.get("html_url")

            else:
                logger.warning("Payload does not contain issue or pull_request")
                return None

            if not all([pr_url, comment_body, pr_number, repo_full_name]):
                logger.warning("Missing required PR information")
                return None

            return {
                "pr_url": pr_url,
                "comment_body": comment_body,
                "pr_number": pr_number,
                "repo_full_name": repo_full_name,
            }

        except Exception as e:
            logger.error(f"Error extracting PR info: {e}")
            return None

    def _build_devin_prompt(self, pr_url: str, comment: str) -> str:
        """
        Build prompt for Devin API.

        Args:
            pr_url: URL of the PR to fix
            comment: Review comment from bot

        Returns:
            Formatted prompt string
        """
        prompt = (
            f"Fix the issues in PR {pr_url} based on the following comment: "
            f'"{comment}". '
            f"Once complete, push the fix to a new branch and create a new pull request."
        )
        return prompt
