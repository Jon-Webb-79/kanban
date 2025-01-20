import os
import sqlite3
from datetime import datetime, timedelta

import pytest

from kanban.kanban import DatabaseManager, KanbanDataError, PeriodManager, TaskManager

# ==========================================================================================
# ==========================================================================================
# File:    test.py
# Date:    January 19, 2025
# Author:  Jonathan A. Webb
# Purpose: Describe the types of testing to occur in this file.
# Instruction: This code can be run in hte following ways
# ==========================================================================================
# ==========================================================================================
# Insert Code here


@pytest.fixture
def db_manager():
    """Fixture to provide a fresh DatabaseManager instance."""
    manager = DatabaseManager()
    yield manager
    # Cleanup after tests
    if manager.conn:
        manager.close()


# --------------------------------------------------------------------------------


@pytest.fixture
def temp_db_file(tmp_path):
    """Fixture to provide a temporary database file path."""
    db_file = tmp_path / "test_kanban.db"
    yield str(db_file)
    # Cleanup after tests
    if os.path.exists(db_file):
        os.remove(db_file)


# --------------------------------------------------------------------------------


class TestDatabaseManager:
    """Test suite for DatabaseManager class."""

    def test_init(self, db_manager):
        """Test initial state of DatabaseManager."""
        assert db_manager.conn is None
        assert db_manager.cursor is None

    # ================================================================================

    class TestConnect:
        def test_successful_connection(self, db_manager, temp_db_file):
            """Test successful database connection."""
            assert db_manager.connect(temp_db_file) is True
            assert db_manager.conn is not None
            assert db_manager.cursor is not None

        # --------------------------------------------------------------------------------

        def test_reconnection(self, db_manager, temp_db_file):
            """Test reconnecting to a different database."""
            # First connection
            db_manager.connect(temp_db_file)
            first_conn = db_manager.conn

            # Second connection
            db_manager.connect(temp_db_file)
            assert db_manager.conn is not first_conn

        # --------------------------------------------------------------------------------

        def test_invalid_permissions(self, db_manager, tmp_path):
            """Test connection with insufficient permissions."""
            db_file = tmp_path / "readonly.db"

            # First create a valid database
            temp_conn = sqlite3.connect(str(db_file))
            temp_conn.close()

            # Make it read-only
            db_file.chmod(0o444)

            # Try to connect and write to the database
            success = db_manager.connect(str(db_file))
            if success:
                try:
                    # Try to write to the database
                    db_manager.cursor.execute("CREATE TABLE test (id INTEGER)")
                    db_manager.conn.commit()
                    assert False, "Should not be able to write to read-only database"
                except sqlite3.OperationalError:
                    # This is what we expect - can't write to read-only database
                    pass

        # --------------------------------------------------------------------------------

        def test_invalid_path(self, db_manager):
            """Test connection with invalid path."""
            assert db_manager.connect("/invalid/path/to/db.db") is False

    # ================================================================================
    # ================================================================================

    class TestCreateSchema:
        def test_successful_schema_creation(self, db_manager, temp_db_file):
            """Test successful schema creation."""
            db_manager.connect(temp_db_file)
            assert db_manager.create_schema() is True

            # Verify tables exist
            tables = db_manager.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t[0] for t in tables]
            assert "performance_periods" in table_names
            assert "tasks" in table_names

        # --------------------------------------------------------------------------------

        def test_create_schema_no_connection(self, db_manager):
            """Test schema creation without database connection."""
            assert db_manager.create_schema() is False

        # --------------------------------------------------------------------------------

        def test_schema_idempotency(self, db_manager, temp_db_file):
            """Test creating schema multiple times."""
            db_manager.connect(temp_db_file)
            assert db_manager.create_schema() is True
            assert db_manager.create_schema() is True  # Should succeed again

    # ================================================================================
    # ================================================================================

    class TestVerifySchema:
        def test_verify_correct_schema(self, db_manager, temp_db_file):
            """Test schema verification with correct schema."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()
            assert db_manager.verify_schema() is True

        # --------------------------------------------------------------------------------

        def test_verify_no_connection(self, db_manager):
            """Test schema verification without connection."""
            assert db_manager.verify_schema() is False

        # --------------------------------------------------------------------------------

        def test_verify_incomplete_schema(self, db_manager, temp_db_file):
            """Test verification with incomplete schema."""
            db_manager.connect(temp_db_file)
            # Create only one table
            db_manager.cursor.execute(
                """
                CREATE TABLE performance_periods (
                    id INTEGER PRIMARY KEY,
                    start_date TEXT,
                    end_date TEXT,
                    name TEXT UNIQUE
                )
                """
            )
            assert db_manager.verify_schema() is False

        # --------------------------------------------------------------------------------

        def test_verify_modified_schema(self, db_manager, temp_db_file):
            """Test verification with modified schema."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()
            # Modify a table
            db_manager.cursor.execute("ALTER TABLE tasks ADD COLUMN extra TEXT")
            assert (
                db_manager.verify_schema() is True
            )  # Should still pass with extra column

    # ================================================================================
    # ================================================================================

    class TestClose:
        def test_successful_close(self, db_manager, temp_db_file):
            """Test successful database closure."""
            db_manager.connect(temp_db_file)
            db_manager.close()
            assert db_manager.conn is None
            assert db_manager.cursor is None

        # --------------------------------------------------------------------------------

        def test_close_without_connection(self, db_manager):
            """Test closing without an active connection."""
            db_manager.close()  # Should not raise any errors
            assert db_manager.conn is None
            assert db_manager.cursor is None

    # --------------------------------------------------------------------------------

    class TestGetCurrentPeriod:
        def test_get_current_period_success(self, db_manager, temp_db_file):
            """Test getting current period with valid data."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()

            # Create a period containing current date
            current_date = datetime.now()
            start_date = (current_date - timedelta(days=5)).date().isoformat()
            end_date = (current_date + timedelta(days=5)).date().isoformat()

            db_manager.cursor.execute(
                """
                INSERT INTO performance_periods (name, start_date, end_date)
                VALUES (?, ?, ?)
                """,
                ("Current Period", start_date, end_date),
            )
            db_manager.conn.commit()

            assert db_manager.get_current_period() == "Current Period"

        # --------------------------------------------------------------------------------

        def test_get_current_period_no_match(self, db_manager, temp_db_file):
            """Test getting current period with no matching period."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()

            # Create a period in the future
            future_date = datetime.now() + timedelta(days=10)
            start_date = future_date.date().isoformat()
            end_date = (future_date + timedelta(days=5)).date().isoformat()

            db_manager.cursor.execute(
                """
                INSERT INTO performance_periods (name, start_date, end_date)
                VALUES (?, ?, ?)
                """,
                ("Future Period", start_date, end_date),
            )
            db_manager.conn.commit()

            assert db_manager.get_current_period() is None

        # --------------------------------------------------------------------------------

        def test_get_current_period_no_connection(self, db_manager):
            """Test getting current period without connection."""
            assert db_manager.get_current_period() is None

        # --------------------------------------------------------------------------------

        def test_get_current_period_multiple_periods(self, db_manager, temp_db_file):
            """Test getting current period with overlapping periods."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()

            current_date = datetime.now()

            # Create two overlapping periods
            periods = [("Period 1", -5, 5), ("Period 2", -3, 3)]

            for name, start_offset, end_offset in periods:
                start_date = (
                    (current_date + timedelta(days=start_offset)).date().isoformat()
                )
                end_date = (current_date + timedelta(days=end_offset)).date().isoformat()

                db_manager.cursor.execute(
                    """
                    INSERT INTO performance_periods (name, start_date, end_date)
                    VALUES (?, ?, ?)
                    """,
                    (name, start_date, end_date),
                )

            db_manager.conn.commit()

            # Should return the first matching period
            assert db_manager.get_current_period() in ["Period 1", "Period 2"]

    # ================================================================================
    # ================================================================================

    class TestTaskValidation:
        """Test suite for task validation functionality"""

        def test_create_task_with_empty_title(self, db_manager, temp_db_file):
            """Test creating task with empty title should raise KanbanDataError."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()
            task_manager = TaskManager(db_manager)

            with pytest.raises(KanbanDataError) as exc:
                task_manager.create_task("", "description", "project")
            assert "Task title cannot be empty" in str(exc.value)

        # --------------------------------------------------------------------------------

        def test_create_task_with_whitespace_title(self, db_manager, temp_db_file):
            """Test creating task with whitespace-only title should raise
            KanbanDataError."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()
            task_manager = TaskManager(db_manager)

            with pytest.raises(KanbanDataError) as exc:
                task_manager.create_task("   ", "description", "project")
            assert "Task title cannot be empty" in str(exc.value)

        # --------------------------------------------------------------------------------

        def test_create_task_with_empty_project(self, db_manager, temp_db_file):
            """Test creating task with empty project should raise
            KanbanDataError."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()
            task_manager = TaskManager(db_manager)

            with pytest.raises(KanbanDataError) as exc:
                task_manager.create_task("title", "description", "")
            assert "Project name cannot be empty" in str(exc.value)

        # --------------------------------------------------------------------------------

        def test_create_task_with_whitespace_project(self, db_manager, temp_db_file):
            """Test creating task with whitespace-only project should raise
            KanbanDataError."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()
            task_manager = TaskManager(db_manager)

            with pytest.raises(KanbanDataError) as exc:
                task_manager.create_task("title", "description", "  ")
            assert "Project name cannot be empty" in str(exc.value)

        # --------------------------------------------------------------------------------

        def test_create_task_without_connection(self, db_manager, temp_db_file):
            """Test creating task without database connection should return None."""
            task_manager = TaskManager(db_manager)  # No connection established

            result = task_manager.create_task("title", "description", "project")
            assert result is None

        # --------------------------------------------------------------------------------

        def test_create_task_with_valid_data(self, db_manager, temp_db_file):
            """Test creating task with valid data should succeed."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()
            task_manager = TaskManager(db_manager)

            task_id = task_manager.create_task(
                "Test Task", "Test Description", "Test Project"
            )
            assert task_id is not None

            # Verify task was created correctly
            db_manager.cursor.execute(
                "SELECT title, description, project, status FROM tasks WHERE id = ?",
                (task_id,),
            )
            task = db_manager.cursor.fetchone()
            assert task is not None
            assert task[0] == "Test Task"
            assert task[1] == "Test Description"
            assert task[2] == "Test Project"
            assert task[3] == "unassigned"

        # --------------------------------------------------------------------------------

        def test_create_task_strips_whitespace(self, db_manager, temp_db_file):
            """Test that whitespace is stripped from title and project."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()
            task_manager = TaskManager(db_manager)

            task_id = task_manager.create_task(
                "  Test Task  ", "Description", "  Test Project  "
            )
            assert task_id is not None

            # Verify whitespace was stripped
            db_manager.cursor.execute(
                "SELECT title, project FROM tasks WHERE id = ?", (task_id,)
            )
            task = db_manager.cursor.fetchone()
            assert task[0] == "Test Task"
            assert task[1] == "Test Project"

        # --------------------------------------------------------------------------------

        def test_create_task_empty_description_allowed(self, db_manager, temp_db_file):
            """Test that empty description is allowed."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()
            task_manager = TaskManager(db_manager)

            task_id = task_manager.create_task("Test Task", "", "Test Project")
            assert task_id is not None

            task_id = task_manager.create_task("Test Task", None, "Test Project")
            assert task_id is not None

    # ================================================================================
    # ================================================================================

    class TestPeriodValidation:
        """Test suite for period validation functionality"""

        def test_create_period_with_empty_name(self, db_manager, temp_db_file):
            """Test creating period with empty name."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()
            period_manager = PeriodManager(db_manager)

            with pytest.raises(KanbanDataError) as exc:
                period_manager.create_period("", "1/1/24", "12/31/24")
            assert "Period name cannot be empty" in str(exc.value)

        # --------------------------------------------------------------------------------

        def test_create_period_with_whitespace_name(self, db_manager, temp_db_file):
            """Test creating period with whitespace-only name."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()
            period_manager = PeriodManager(db_manager)

            with pytest.raises(KanbanDataError) as exc:
                period_manager.create_period("   ", "1/1/24", "12/31/24")
            assert "Period name cannot be empty" in str(exc.value)

        # --------------------------------------------------------------------------------

        def test_create_period_with_invalid_dates(self, db_manager, temp_db_file):
            """Test creating period with invalid date format."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()
            period_manager = PeriodManager(db_manager)

            with pytest.raises(KanbanDataError) as exc:
                period_manager.create_period("Test Period", "invalid-date", "12/31/24")
            assert "Invalid date format" in str(exc.value)

        # --------------------------------------------------------------------------------

        def test_create_period_with_end_before_start(self, db_manager, temp_db_file):
            """Test creating period with end date before start date."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()
            period_manager = PeriodManager(db_manager)

            with pytest.raises(KanbanDataError) as exc:
                period_manager.create_period("Test Period", "12/31/24", "1/1/24")
            assert "End date cannot be before start date" in str(exc.value)

        # --------------------------------------------------------------------------------

        def test_create_duplicate_period(self, db_manager, temp_db_file):
            """Test creating period with duplicate name."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()
            period_manager = PeriodManager(db_manager)

            # Create first period
            period_manager.create_period("Test Period", "1/1/24", "6/30/24")

            # Try to create second period with same name
            with pytest.raises(KanbanDataError) as exc:
                period_manager.create_period("Test Period", "7/1/24", "12/31/24")
            assert "already exists" in str(exc.value)

        # --------------------------------------------------------------------------------

        def test_create_period_without_connection(self, db_manager):
            """Test creating period without database connection."""
            period_manager = PeriodManager(db_manager)  # No connection established

            result = period_manager.create_period("Test Period", "1/1/24", "12/31/24")
            assert result is None

        # --------------------------------------------------------------------------------

        def test_create_valid_period(self, db_manager, temp_db_file):
            """Test creating period with valid data."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()
            period_manager = PeriodManager(db_manager)

            period_id = period_manager.create_period("Test Period", "1/1/24", "12/31/24")
            assert period_id is not None

            # Verify period was created correctly
            db_manager.cursor.execute(
                "SELECT name, start_date, end_date FROM performance_periods WHERE id = ?",
                (period_id,),
            )
            period = db_manager.cursor.fetchone()
            assert period is not None
            assert period[0] == "Test Period"
            # The dates will be stored in ISO format in the database
            assert period[1] == "2024-01-01"
            assert period[2] == "2024-12-31"

        # --------------------------------------------------------------------------------

        def test_create_period_strips_whitespace(self, db_manager, temp_db_file):
            """Test that whitespace is stripped from period name."""
            db_manager.connect(temp_db_file)
            db_manager.create_schema()
            period_manager = PeriodManager(db_manager)

            period_id = period_manager.create_period(
                "  Test Period  ", "1/1/24", "12/31/24"
            )
            assert period_id is not None

            # Verify whitespace was stripped
            db_manager.cursor.execute(
                "SELECT name FROM performance_periods WHERE id = ?", (period_id,)
            )
            period = db_manager.cursor.fetchone()
            assert period[0] == "Test Period"


# ==========================================================================================
# ==========================================================================================
# eof
