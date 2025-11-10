"""Unit tests for SessionRepository."""
import pytest
from pathlib import Path
from app.repositories.session_repository import SessionRepository
from app.core.exceptions import RepositoryError, SessionNotFoundError


@pytest.fixture
def temp_db_path(tmp_path):
    """Create temporary database path."""
    return str(tmp_path / "test_sessions.json")


@pytest.fixture
def session_repo(temp_db_path):
    """Create SessionRepository instance."""
    return SessionRepository(db_path=temp_db_path)


class TestSessionRepositoryInit:
    """Tests for SessionRepository initialization."""

    def test_init_creates_directory(self, tmp_path):
        """Test that initialization creates directory."""
        db_path = str(tmp_path / "subdir" / "sessions.json")
        SessionRepository(db_path=db_path)
        assert Path(db_path).parent.exists()

    def test_init_creates_empty_db(self, temp_db_path):
        """Test that initialization creates empty database."""
        repo = SessionRepository(db_path=temp_db_path)
        assert Path(temp_db_path).exists()
        sessions = repo.get_pending_sessions()
        assert sessions == []


class TestSessionRepositoryAddPendingSession:
    """Tests for add_pending_session method."""

    def test_add_pending_session(self, session_repo):
        """Test adding a pending session."""
        session_repo.add_pending_session(
            session_id="test_session_123",
            original_pr_number=1,
            repo_full_name="owner/repo",
            comment_body="Test comment",
        )

        sessions = session_repo.get_pending_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "test_session_123"
        assert sessions[0]["status"] == "pending"

    def test_add_duplicate_session(self, session_repo):
        """Test adding duplicate session."""
        session_repo.add_pending_session(
            session_id="test_session_123",
            original_pr_number=1,
            repo_full_name="owner/repo",
        )
        session_repo.add_pending_session(
            session_id="test_session_123",
            original_pr_number=1,
            repo_full_name="owner/repo",
        )

        sessions = session_repo.get_pending_sessions()
        assert len(sessions) == 1


class TestSessionRepositoryGetPendingSessions:
    """Tests for get_pending_sessions method."""

    def test_get_pending_sessions_empty(self, session_repo):
        """Test getting pending sessions when empty."""
        sessions = session_repo.get_pending_sessions()
        assert sessions == []

    def test_get_pending_sessions_filtered(self, session_repo):
        """Test that only pending sessions are returned."""
        session_repo.add_pending_session(
            session_id="pending_1",
            original_pr_number=1,
            repo_full_name="owner/repo",
        )
        session_repo.add_pending_session(
            session_id="pending_2",
            original_pr_number=2,
            repo_full_name="owner/repo",
        )
        session_repo.mark_session_completed("pending_1")

        sessions = session_repo.get_pending_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "pending_2"


class TestSessionRepositoryMarkSessionCompleted:
    """Tests for mark_session_completed method."""

    def test_mark_session_completed(self, session_repo):
        """Test marking session as completed."""
        session_repo.add_pending_session(
            session_id="test_session_123",
            original_pr_number=1,
            repo_full_name="owner/repo",
        )

        session_repo.mark_session_completed(
            "test_session_123", new_pr_url="https://github.com/owner/repo/pull/2"
        )

        session = session_repo.get_session("test_session_123")
        assert session["status"] == "completed"
        assert session["new_pr_url"] == "https://github.com/owner/repo/pull/2"

    def test_mark_session_completed_not_found(self, session_repo):
        """Test marking non-existent session as completed."""
        with pytest.raises(SessionNotFoundError):
            session_repo.mark_session_completed("non_existent")


class TestSessionRepositoryMarkSessionFailed:
    """Tests for mark_session_failed method."""

    def test_mark_session_failed(self, session_repo):
        """Test marking session as failed."""
        session_repo.add_pending_session(
            session_id="test_session_123",
            original_pr_number=1,
            repo_full_name="owner/repo",
        )

        session_repo.mark_session_failed("test_session_123", error_message="Test error")

        session = session_repo.get_session("test_session_123")
        assert session["status"] == "failed"
        assert session["error_message"] == "Test error"

    def test_mark_session_failed_not_found(self, session_repo):
        """Test marking non-existent session as failed."""
        with pytest.raises(SessionNotFoundError):
            session_repo.mark_session_failed("non_existent")


class TestSessionRepositoryGetSession:
    """Tests for get_session method."""

    def test_get_session_exists(self, session_repo):
        """Test getting existing session."""
        session_repo.add_pending_session(
            session_id="test_session_123",
            original_pr_number=1,
            repo_full_name="owner/repo",
        )

        session = session_repo.get_session("test_session_123")
        assert session is not None
        assert session["session_id"] == "test_session_123"

    def test_get_session_not_exists(self, session_repo):
        """Test getting non-existent session."""
        session = session_repo.get_session("non_existent")
        assert session is None


class TestSessionRepositoryErrorHandling:
    """Tests for error handling."""

    def test_read_db_invalid_json(self, temp_db_path):
        """Test reading invalid JSON."""
        Path(temp_db_path).write_text("invalid json")
        repo = SessionRepository(db_path=temp_db_path)

        with pytest.raises(RepositoryError):
            repo.get_pending_sessions()

    def test_write_db_permission_error(self, temp_db_path, monkeypatch):
        """Test writing with permission error."""
        repo = SessionRepository(db_path=temp_db_path)

        def mock_write_text(*args, **kwargs):
            raise PermissionError("Permission denied")

        monkeypatch.setattr(Path(temp_db_path), "write_text", mock_write_text)

        with pytest.raises(RepositoryError):
            repo.add_pending_session(
                session_id="test",
                original_pr_number=1,
                repo_full_name="owner/repo",
            )
