"""Monitor script for polling Devin session status."""
import asyncio
import logging
import sys
from typing import Optional, Dict, Any
from app.clients.devin_client import DevinClient
from app.clients.github_client import GitHubClient
from app.repositories.session_repository import SessionRepository
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SessionMonitor:
    """Monitor for Devin sessions."""

    def __init__(self):
        """Initialize session monitor."""
        self.devin_client = DevinClient()
        self.session_repo = SessionRepository()
        # GitHub client will be initialized when needed (requires token)
        self.github_client: Optional[GitHubClient] = None

    async def check_sessions(self):
        """Check status of all pending sessions."""
        pending_sessions = self.session_repo.get_pending_sessions()
        if not pending_sessions:
            logger.debug("No pending sessions to monitor")
            return

        logger.info(f"Checking {len(pending_sessions)} pending session(s)")

        for session in pending_sessions:
            session_id = session.get("session_id")
            if not session_id:
                continue

            await self._check_session(session)

    async def _check_session(self, session: Dict[str, Any]):
        """
        Check status of a single session.

        Args:
            session: Session dictionary from repository
        """
        session_id = session.get("session_id")
        logger.debug(f"Checking session {session_id}")

        # Get session status from Devin API
        session_data = await self.devin_client.get_session_status(session_id)
        if not session_data:
            logger.warning(f"Could not get status for session {session_id}")
            return

        status_enum = session_data.get("status_enum", "").lower()

        if status_enum == "working":
            logger.debug(f"Session {session_id} is still working")
            return

        elif status_enum == "finished":
            logger.info(f"Session {session_id} has finished")
            await self._handle_finished_session(session, session_data)

        elif status_enum == "blocked":
            logger.warning(f"Session {session_id} is blocked")
            error_message = session_data.get("error_message", "Session blocked")
            self.session_repo.mark_session_failed(session_id, error_message)

        else:
            logger.warning(f"Unknown status '{status_enum}' for session {session_id}")

    async def _handle_finished_session(
        self, session: Dict[str, Any], session_data: Dict[str, Any]
    ):
        """
        Handle a finished session.

        Args:
            session: Session dictionary from repository
            session_data: Full session data from Devin API
        """
        session_id = session.get("session_id")
        repo_full_name = session.get("repo_full_name", "")
        original_pr_number = session.get("original_pr_number")

        # Extract new PR URL from session data
        new_pr_url = None

        # Try to get PR URL from structured_output or pull_request field
        structured_output = session_data.get("structured_output")
        if structured_output:
            if isinstance(structured_output, dict):
                new_pr_url = structured_output.get("pull_request_url") or structured_output.get(
                    "pr_url"
                )

        # Also check pull_request field directly
        if not new_pr_url:
            pull_request = session_data.get("pull_request")
            if isinstance(pull_request, dict):
                new_pr_url = pull_request.get("html_url") or pull_request.get("url")

        # Mark session as completed
        self.session_repo.mark_session_completed(session_id, new_pr_url)

        # Post comment on original PR if we have the information
        if repo_full_name and original_pr_number:
            await self._post_completion_comment(
                repo_full_name, original_pr_number, new_pr_url
            )

    async def _post_completion_comment(
        self, repo_full_name: str, pr_number: int, new_pr_url: Optional[str]
    ):
        """
        Post a comment on the original PR about the completion.

        Args:
            repo_full_name: Repository full name (owner/repo)
            pr_number: Original PR number
            new_pr_url: URL of the new PR created by Devin
        """
        # Initialize GitHub client if needed
        # Note: This requires GITHUB_TOKEN in settings
        # For now, we'll skip if token is not available
        try:
            github_token = settings.github_token
            if not github_token:
                logger.debug("GitHub token not configured, skipping comment")
                return

            if not self.github_client:
                self.github_client = GitHubClient(github_token=github_token)

            owner, repo = repo_full_name.split("/", 1)

            if new_pr_url:
                comment_body = (
                    f"✅ Devinが修正版のPRを作成しました。\n\n"
                    f"確認をお願いします: {new_pr_url}"
                )
            else:
                comment_body = (
                    "✅ Devinセッションが完了しました。\n\n"
                    "新しいPRのURLを取得できませんでした。"
                )

            success = await self.github_client.create_comment(
                owner=owner, repo=repo, issue_number=pr_number, body=comment_body
            )

            if success:
                logger.info(
                    f"Posted completion comment on {repo_full_name}#{pr_number}"
                )
            else:
                logger.warning(
                    f"Failed to post comment on {repo_full_name}#{pr_number}"
                )

        except Exception as e:
            logger.error(f"Error posting completion comment: {e}")

    async def run(self):
        """Run the monitor loop."""
        logger.info("Starting Devin session monitor")
        logger.info(f"Poll interval: {settings.monitor_poll_interval} seconds")

        try:
            while True:
                await self.check_sessions()
                await asyncio.sleep(settings.monitor_poll_interval)
        except KeyboardInterrupt:
            logger.info("Monitor stopped by user")
        except Exception as e:
            logger.error(f"Monitor error: {e}", exc_info=True)
        finally:
            await self.devin_client.close()
            if self.github_client:
                await self.github_client.close()


async def main():
    """Main entry point."""
    monitor = SessionMonitor()
    await monitor.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Monitor stopped")
        sys.exit(0)
