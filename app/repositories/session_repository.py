"""Session repository for managing pending Devin sessions."""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.exceptions import RepositoryError, SessionNotFoundError

logger = get_logger(__name__)


class SessionRepository:
    """Repository for managing Devin session state."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize session repository.

        Args:
            db_path: Path to JSON database file. Defaults to settings value.
        """
        self.db_path = Path(db_path or settings.session_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize empty database if it doesn't exist
        if not self.db_path.exists():
            self._write_db([])

    def _read_db(self) -> List[Dict[str, Any]]:
        """Read session database from file."""
        try:
            if not self.db_path.exists():
                return []
            content = self.db_path.read_text(encoding="utf-8")
            return json.loads(content) if content.strip() else []
        except json.JSONDecodeError as e:
            error_msg = f"Error reading session database: {e}"
            logger.error(error_msg, extra={"db_path": str(self.db_path)})
            raise RepositoryError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error reading session database: {e}"
            logger.error(error_msg, exc_info=True, extra={"db_path": str(self.db_path)})
            raise RepositoryError(error_msg)

    def _write_db(self, data: List[Dict[str, Any]]):
        """Write session database to file."""
        try:
            self.db_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            error_msg = f"Error writing session database: {e}"
            logger.error(error_msg, exc_info=True, extra={"db_path": str(self.db_path)})
            raise RepositoryError(error_msg)

    def add_pending_session(
        self,
        session_id: str,
        original_pr_number: int,
        repo_full_name: str,
        comment_body: Optional[str] = None,
    ):
        """
        Add a new pending session to the database.

        Args:
            session_id: Devin session ID
            original_pr_number: Original PR number
            repo_full_name: Repository full name (owner/repo)
            comment_body: Optional comment body for reference
        """
        data = self._read_db()

        # Check if session already exists
        for session in data:
            if session.get("session_id") == session_id:
                logger.warning(f"Session {session_id} already exists in database")
                return

        new_session = {
            "session_id": session_id,
            "repo_full_name": repo_full_name,
            "original_pr_number": original_pr_number,
            "comment_body": comment_body,
            "status": "pending",
        }
        data.append(new_session)
        self._write_db(data)
        logger.info(f"Added pending session {session_id} for {repo_full_name}#{original_pr_number}")

    def get_pending_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all pending sessions.

        Returns:
            List of pending session dictionaries
        """
        data = self._read_db()
        return [s for s in data if s.get("status") == "pending"]

    def mark_session_completed(
        self, session_id: str, new_pr_url: Optional[str] = None
    ):
        """
        Mark a session as completed.

        Args:
            session_id: Devin session ID
            new_pr_url: Optional URL of the new PR created by Devin
        """
        data = self._read_db()
        updated = False

        for session in data:
            if session.get("session_id") == session_id:
                session["status"] = "completed"
                if new_pr_url:
                    session["new_pr_url"] = new_pr_url
                updated = True
                break

        if updated:
            self._write_db(data)
            logger.info(
                f"Marked session {session_id} as completed",
                extra={"session_id": session_id, "new_pr_url": new_pr_url},
            )
        else:
            error_msg = f"Session {session_id} not found in database"
            logger.warning(error_msg, extra={"session_id": session_id})
            raise SessionNotFoundError(error_msg)

    def mark_session_failed(self, session_id: str, error_message: Optional[str] = None):
        """
        Mark a session as failed.

        Args:
            session_id: Devin session ID
            error_message: Optional error message
        """
        data = self._read_db()
        updated = False

        for session in data:
            if session.get("session_id") == session_id:
                session["status"] = "failed"
                if error_message:
                    session["error_message"] = error_message
                updated = True
                break

        if updated:
            self._write_db(data)
            logger.info(
                f"Marked session {session_id} as failed",
                extra={"session_id": session_id, "error_message": error_message},
            )
        else:
            error_msg = f"Session {session_id} not found in database"
            logger.warning(error_msg, extra={"session_id": session_id})
            raise SessionNotFoundError(error_msg)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific session by ID.

        Args:
            session_id: Devin session ID

        Returns:
            Session dictionary if found, None otherwise
        """
        data = self._read_db()
        for session in data:
            if session.get("session_id") == session_id:
                return session
        return None
