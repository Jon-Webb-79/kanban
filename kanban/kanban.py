import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Tuple

import customtkinter as ctk
import pandas as pd

# from PIL import Image, ImageTk
from tkcalendar import DateEntry

# ================================================================================
# ================================================================================


class KanbanDataError(Exception):
    """Exception raised for data validation errors in Kanban manager."""

    pass


# ================================================================================


class DatabaseManager:
    """
    Handles all database operations and queries for the Kanban Task Manager.

    This class manages the SQLite database connection and provides methods for
    database operations including schema creation, verification, and period management.

    Attributes:
        conn (Optional[sqlite3.Connection]): SQLite database connection object
        cursor (Optional[sqlite3.Cursor]): Database cursor for executing SQL commands
    """

    def __init__(self):
        """Initialize DatabaseManager with no active connection."""
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

    def connect(self, filename: str) -> bool:
        """
        Establish a connection to a SQLite database file.

        Args:
            filename (str): Path to the SQLite database file

        Returns:
            bool: True if connection successful, False otherwise

        Raises:
            sqlite3.Error: If database connection fails
        """
        try:
            if self.conn:
                self.conn.close()

            self.conn = sqlite3.connect(filename)
            self.cursor = self.conn.cursor()
            return True
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            return False

    # --------------------------------------------------------------------------------

    def create_schema(self) -> bool:
        """
        Create the database schema if it doesn't exist.

        Creates two tables:
            - performance_periods: Stores period information
            - tasks: Stores task information with foreign key to periods

        Returns:
            bool: True if schema creation successful, False otherwise

        Raises:
            sqlite3.Error: If schema creation fails
        """
        try:
            if not self.conn or not self.cursor:
                return False

            # Create performance periods table
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS performance_periods (
                    id INTEGER PRIMARY KEY,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    name TEXT UNIQUE NOT NULL
                )
            """
            )

            # Create tasks table with NOT NULL constraints
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    resource TEXT,
                    project TEXT NOT NULL,
                    period_id INTEGER,
                    created_datetime TEXT NOT NULL,
                    todo_datetime TEXT,
                    inwork_datetime TEXT,
                    completed_datetime TEXT,
                    FOREIGN KEY (period_id) REFERENCES performance_periods(id)
                )
            """
            )

            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Schema creation error: {e}")
            return False

    # --------------------------------------------------------------------------------

    def verify_schema(self) -> bool:
        """
        Verify that the database has the correct schema structure.

        Checks for the existence of required tables and their columns:
            - performance_periods: id, start_date, end_date, name
            - tasks: all task-related columns including timestamps

        Returns:
            bool: True if schema verification successful, False otherwise

        Raises:
            sqlite3.Error: If schema verification fails
        """
        try:
            if not self.conn or not self.cursor:
                return False

            required_tables = {
                "performance_periods": ["id", "start_date", "end_date", "name"],
                "tasks": [
                    "id",
                    "title",
                    "description",
                    "status",
                    "resource",
                    "project",
                    "period_id",
                    "created_datetime",
                    "todo_datetime",
                    "inwork_datetime",
                    "completed_datetime",
                ],
            }

            for table, columns in required_tables.items():
                self.cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                )
                if not self.cursor.fetchone():
                    return False

                self.cursor.execute(f"PRAGMA table_info({table})")
                existing_columns = [row[1] for row in self.cursor.fetchall()]

                if not all(col in existing_columns for col in columns):
                    return False

            return True
        except sqlite3.Error as e:
            print(f"Schema verification error: {e}")
            return False

    # --------------------------------------------------------------------------------

    def close(self):
        """
        Close the database connection and reset connection objects.

        This method ensures proper cleanup of database resources by closing
        the active connection and setting connection objects to None.
        """
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    # --------------------------------------------------------------------------------

    def get_current_period(self) -> Optional[str]:
        """
        Get the period name that contains the current date.

        Queries the performance_periods table to find a period where the current
        date falls between the start_date and end_date.

        Returns:
            Optional[str]: Name of the current period if found, None otherwise

        Raises:
            sqlite3.Error: If database query fails
        """
        try:
            if not self.conn or not self.cursor:
                return None

            current_date = datetime.now().date()

            self.cursor.execute(
                """
                SELECT name
                FROM performance_periods
                WHERE date(start_date) <= date(?)
                AND date(end_date) >= date(?)
            """,
                (current_date.isoformat(), current_date.isoformat()),
            )

            result = self.cursor.fetchone()
            return result[0] if result else None

        except sqlite3.Error as e:
            print(f"Error getting current period: {e}")
            return None

    # --------------------------------------------------------------------------------

    def validate_task_data(self, title: str, project: str) -> None:
        """
        Validate task data before insertion or update.

        Args:
            title (str): Task title
            project (str): Project name

        Raises:
            KanbanDataError: If validation fails
        """
        if not title or not title.strip():
            raise KanbanDataError("Task title cannot be empty")
        if not project or not project.strip():
            raise KanbanDataError("Project name cannot be empty")

    # --------------------------------------------------------------------------------

    def validate_period_data(self, name: str, start_date: str, end_date: str) -> None:
        """
        Validate period data before insertion or update.

        Args:
            name (str): Sprint name
            start_date (str): Sprint start date (MM/DD/YY)
            end_date (str): Sprint end date (MM/DD/YY)

        Raises:
            KanbanDataError: If validation fails
        """
        # Check for empty name
        if not name or not name.strip():
            raise KanbanDataError("Sprint name cannot be empty")

        try:
            # Parse dates using datetime.strptime for MM/DD/YY format
            start = datetime.strptime(start_date, "%m/%d/%y").date()

            end = datetime.strptime(end_date, "%m/%d/%y").date()

            # Check date order
            if end < start:
                raise KanbanDataError("End date cannot be before start date")

        except ValueError as error:  # Only catch date parsing errors
            print(f"Debug - Date parsing error: {str(error)}")
            raise KanbanDataError("Invalid date format")

        # Check for existing period name after dates are validated
        if self.conn and self.cursor:
            self.cursor.execute(
                "SELECT name FROM performance_periods WHERE name = ?", (name.strip(),)
            )
            if self.cursor.fetchone():
                raise KanbanDataError(f"Sprint with name '{name}' already exists")


# ================================================================================
# ================================================================================


class TaskManager:
    """
    Manages task-related operations for the Kanban system.

    This class handles all task operations including creation, status updates,
    and queries. It works in conjunction with the DatabaseManager to persist
    task data.

    Attributes:
        db (DatabaseManager): Database manager instance for data persistence
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize TaskManager with a database manager.

        Args:
            db_manager (DatabaseManager): Database manager instance for task operations
        """
        self.db = db_manager

    def create_task(self, title: str, description: str, project: str) -> Optional[int]:
        """
        Create a new task with validation.

        Creates a new task in the database with provided details. The task
        is initially created with 'unassigned' status and validates required
        fields before creation.

        Args:
            title (str): Task title
            description (str): Task description
            project (str): Project name

        Returns:
            Optional[int]: ID of the created task if successful, None if failed

        Raises:
            KanbanDataError: If task data validation fails (empty title or project)
            sqlite3.Error: If database operation fails
        """
        try:
            if not self.db.conn or not self.db.cursor:
                return None

            self.db.validate_task_data(title, project)
            self.db.cursor.execute(
                """
                INSERT INTO tasks (
                    title, description, status, project, created_datetime
                ) VALUES (?, ?, ?, ?, ?)
            """,
                (
                    title.strip(),
                    description,
                    "unassigned",
                    project.strip(),
                    datetime.now().isoformat(),
                ),
            )

            self.db.conn.commit()
            return self.db.cursor.lastrowid

        except sqlite3.Error as e:
            print(f"Task creation error: {e}")
            return None

    def move_to_todo(self, task_id: int, period_id: int) -> bool:
        """
        Move a task to Todo status.

        Updates the task's status to 'todo' and assigns it to a specific period.
        Also records the timestamp when the task was moved to todo status.

        Args:
            task_id (int): ID of the task to move
            period_id (int): ID of the period to assign the task to

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.db.conn or not self.db.cursor:
                return False

            self.db.cursor.execute(
                """
                UPDATE tasks
                SET status = 'todo',
                    period_id = ?,
                    todo_datetime = ?
                WHERE id = ?
            """,
                (period_id, datetime.now().isoformat(), task_id),
            )

            self.db.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Move to todo error: {e}")
            return False

    def assign_resource(self, task_id: int, resource: str) -> bool:
        """
        Assign a resource to a task.

        Updates the task to assign a specific resource (typically a person)
        to be responsible for the task.

        Args:
            task_id (int): ID of the task to assign
            resource (str): Name or identifier of the resource

        Returns:
            bool: True if assignment successful, False otherwise
        """
        try:
            if not self.db.conn or not self.db.cursor:
                return False

            self.db.cursor.execute(
                """
                UPDATE tasks
                SET resource = ?
                WHERE id = ?
            """,
                (resource, task_id),
            )

            self.db.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Resource assignment error: {e}")
            return False

    def start_task(self, task_id: int) -> bool:
        """
        Move task to In Work status.

        Updates the task status to 'inwork' and records the timestamp
        when work was started.

        Args:
            task_id (int): ID of the task to start

        Returns:
            bool: True if status update successful, False otherwise
        """
        try:
            if not self.db.conn or not self.db.cursor:
                return False

            self.db.cursor.execute(
                """
                UPDATE tasks
                SET status = 'inwork',
                    inwork_datetime = ?
                WHERE id = ?
            """,
                (datetime.now().isoformat(), task_id),
            )

            self.db.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Start task error: {e}")
            return False

    def complete_task(self, task_id: int) -> bool:
        """
        Move task to Completed status.

        Updates the task status to 'completed' and records the completion
        timestamp.

        Args:
            task_id (int): ID of the task to complete

        Returns:
            bool: True if status update successful, False otherwise
        """
        try:
            if not self.db.conn or not self.db.cursor:
                return False

            self.db.cursor.execute(
                """
                UPDATE tasks
                SET status = 'completed',
                    completed_datetime = ?
                WHERE id = ?
            """,
                (datetime.now().isoformat(), task_id),
            )

            self.db.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Complete task error: {e}")
            return False

    def get_tasks_by_period(self, period_id: int) -> List[Dict]:
        """
        Get all tasks for a specific period.

        Retrieves all non-unassigned tasks associated with the specified period.

        Args:
            period_id (int): ID of the period to get tasks for

        Returns:
            List[Dict]: List of tasks, each task represented as a dictionary
                with keys: id, title, description, status, resource, project.
                Returns empty list if no tasks found or on error.
        """
        try:
            if not self.db.conn or not self.db.cursor:
                return []

            self.db.cursor.execute(
                """
                SELECT id, title, description, status, resource, project
                FROM tasks
                WHERE period_id = ? AND status != 'unassigned'
            """,
                (period_id,),
            )

            columns = ["id", "title", "description", "status", "resource", "project"]
            return [dict(zip(columns, row)) for row in self.db.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Get tasks error: {e}")
            return []

    def get_unassigned_tasks(self) -> List[Dict]:
        """
        Get all unassigned tasks.

        Retrieves all tasks with 'unassigned' status.

        Returns:
            List[Dict]: List of unassigned tasks, each task represented as a dictionary
                with keys: id, title, description, project, resource, status.
                Returns empty list if no tasks found or on error.
        """
        try:
            if not self.db.conn or not self.db.cursor:
                return []

            self.db.cursor.execute(
                """
                SELECT id, title, description, project, resource, status
                FROM tasks
                WHERE status = 'unassigned'
            """
            )

            columns = ["id", "title", "description", "project", "resource", "status"]
            return [dict(zip(columns, row)) for row in self.db.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Get unassigned tasks error: {e}")
            return []


# ================================================================================
# ================================================================================


class SprintManager:
    """
    Manages performance periods in the Kanban system.

    This class handles all operations related to performance periods including
    creation, retrieval, and validation. Performance periods are used to organize
    tasks into specific time frames.

    Attributes:
        db (DatabaseManager): Database manager instance for data persistence
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize SprintManager with a database manager.

        Args:
            db_manager (DatabaseManager): Database manager instance for period operations
        """
        self.db = db_manager

    def create_period(self, name: str, start_date: str, end_date: str) -> Optional[int]:
        """
        Create a new performance period with validation.

        Creates a new period in the database with the specified name and date range.
        Dates are expected in MM/DD/YY format and are converted to ISO format for storage.
        The period name must be unique.

        Args:
            name (str): Sprint name
            start_date (str): Start date in MM/DD/YY format (e.g., "01/15/24")
            end_date (str): End date in MM/DD/YY format (e.g., "02/15/24")

        Returns:
            Optional[int]: ID of created period if successful, None if failed

        Raises:
            KanbanDataError: If period validation fails (invalid dates, duplicate name)
            sqlite3.Error: If database operation fails

        Example:
            >>> period_id = period_manager.create_period("Sprint 1", "1/1/24", "1/15/24")
            >>> if period_id is not None:
            ...     print(f"Created period with ID: {period_id}")
        """
        try:
            if not self.db.conn or not self.db.cursor:
                return None

            # Validate period data
            self.db.validate_period_data(name, start_date, end_date)

            # Convert dates to ISO format for storage
            start_iso = datetime.strptime(start_date, "%m/%d/%y").date().isoformat()
            end_iso = datetime.strptime(end_date, "%m/%d/%y").date().isoformat()

            self.db.cursor.execute(
                """
                INSERT INTO performance_periods (name, start_date, end_date)
                VALUES (?, ?, ?)
            """,
                (name.strip(), start_iso, end_iso),
            )

            self.db.conn.commit()
            return self.db.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Sprint creation error: {e}")
            return None

    def get_all_periods(self) -> List[Dict]:
        """
        Get all performance periods ordered by start date.

        Retrieves all periods from the database, ordered chronologically by
        start date.

        Returns:
            List[Dict]: List of periods, each period represented as a dictionary
                with keys: id, name, start_date, end_date.
                Returns empty list if no periods found or on error.

        Example:
            >>> periods = period_manager.get_all_periods()
            >>> for period in periods:
            ...     print(f"{period['name']}: {period['start_date']} to
                          {period['end_date']}")
        """
        try:
            if not self.db.conn or not self.db.cursor:
                return []

            self.db.cursor.execute(
                """
                SELECT id, name, start_date, end_date
                FROM performance_periods
                ORDER BY start_date
            """
            )

            columns = ["id", "name", "start_date", "end_date"]
            return [dict(zip(columns, row)) for row in self.db.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Get periods error: {e}")
            return []

    def get_period_by_name(self, name: str) -> Optional[Dict]:
        """
        Get a period by its name.

        Retrieves a specific period from the database using its unique name.

        Args:
            name (str): Name of the period to retrieve

        Returns:
            Optional[Dict]: Dictionary containing period details with keys:
                id, name, start_date, end_date.
                Returns None if period not found or on error.

        Example:
            >>> period = period_manager.get_period_by_name("Sprint 1")
            >>> if period:
            ...     print(f"Found period: {period['start_date']} to {period['end_date']}")
            ... else:
            ...     print("Sprint not found")
        """
        try:
            if not self.db.conn or not self.db.cursor:
                return None

            self.db.cursor.execute(
                """
                SELECT id, name, start_date, end_date
                FROM performance_periods
                WHERE name = ?
            """,
                (name,),
            )

            row = self.db.cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "start_date": row[2],
                    "end_date": row[3],
                }
            return None
        except sqlite3.Error as e:
            print(f"Get period error: {e}")
            return None


# ================================================================================
# ================================================================================


class StatisticsManager:
    """
    Handles statistical calculations and reporting for the Kanban system.

    This class provides functionality for calculating metrics and generating reports
    about task completion, resource utilization, and project performance. It uses
    pandas for data analysis and can analyze either all tasks or tasks within a
    specific period.

    Attributes:
        db (DatabaseManager): Database manager instance for data access
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize StatisticsManager with a database manager.

        Args:
            db_manager (DatabaseManager): Database manager instance for
            statistics operations
        """
        self.db = db_manager

    def calculate_task_metrics(self, period_id: Optional[int] = None) -> Dict:
        """
        Calculate various task metrics for completed tasks.

        Calculates metrics including average completion times, task counts, and
        breakdowns by resource and project. All time-based metrics are returned
        in hours.

        Args:
            period_id (Optional[int]): ID of period to analyze. If None,
            analyzes all periods.

        Returns:
            Dict: Dictionary containing the following metrics:
                - total_tasks (int): Total number of completed tasks
                - avg_todo_to_inwork (float): Average time from todo to
                  in-work status (hours)
                - avg_inwork_to_complete (float): Average time from in-work
                  to completion (hours)
                - avg_total_time (float): Average total time from todo to
                  completion (hours)
                - by_resource (Dict): Metrics broken down by resource:
                    - tasks_completed (int): Number of tasks completed by
                      resource
                    - avg_completion_time (float): Average completion time by
                      resource
                - by_project (Dict): Metrics broken down by project:
                    - tasks_completed (int): Number of tasks completed by
                      project
                    - avg_completion_time (float): Average completion time by
                      project
                Returns empty dictionary with zero values if no tasks found
                or on error.
        """
        try:
            if not self.db.conn or not self.db.cursor:
                return {}

            query = """
                SELECT
                    status,
                    todo_datetime,
                    inwork_datetime,
                    completed_datetime,
                    resource,
                    project
                FROM tasks
                WHERE status = 'completed'
            """

            if period_id:
                query += " AND period_id = ?"
                self.db.cursor.execute(query, (period_id,))
            else:
                self.db.cursor.execute(query)

            tasks = self.db.cursor.fetchall()

            # Convert to DataFrame for analysis
            df = pd.DataFrame(
                tasks,
                columns=[
                    "status",
                    "todo_dt",
                    "inwork_dt",
                    "completed_dt",
                    "resource",
                    "project",
                ],
            )

            if df.empty:
                return {
                    "total_tasks": 0,
                    "avg_todo_to_inwork": 0,
                    "avg_inwork_to_complete": 0,
                    "avg_total_time": 0,
                    "by_resource": {},
                    "by_project": {},
                }

            # Convert datetime strings to datetime objects
            for col in ["todo_dt", "inwork_dt", "completed_dt"]:
                df[col] = pd.to_datetime(df[col])

            metrics = {
                "total_tasks": len(df),
                "avg_todo_to_inwork": (df["inwork_dt"] - df["todo_dt"])
                .mean()
                .total_seconds()
                / 3600,
                "avg_inwork_to_complete": (df["completed_dt"] - df["inwork_dt"])
                .mean()
                .total_seconds()
                / 3600,
                "avg_total_time": (df["completed_dt"] - df["todo_dt"])
                .mean()
                .total_seconds()
                / 3600,
            }

            # Calculate metrics by resource
            by_resource = (
                df.groupby("resource")
                .agg(
                    {
                        "status": "count",
                        "todo_dt": lambda x: (df["completed_dt"] - x)
                        .mean()
                        .total_seconds()
                        / 3600,
                    }
                )
                .rename(
                    columns={
                        "status": "tasks_completed",
                        "todo_dt": "avg_completion_time",
                    }
                )
            )

            metrics["by_resource"] = by_resource.to_dict("index")

            # Calculate metrics by project
            by_project = (
                df.groupby("project")
                .agg(
                    {
                        "status": "count",
                        "todo_dt": lambda x: (df["completed_dt"] - x)
                        .mean()
                        .total_seconds()
                        / 3600,
                    }
                )
                .rename(
                    columns={
                        "status": "tasks_completed",
                        "todo_dt": "avg_completion_time",
                    }
                )
            )

            metrics["by_project"] = by_project.to_dict("index")

            return metrics

        except (sqlite3.Error, pd.Error) as e:
            print(f"Error calculating metrics: {e}")
            return {}

    def get_task_history(self, period_id: Optional[int] = None) -> List[Dict]:
        """
        Get detailed task history for analysis.

        Retrieves complete task history including all timestamps and status changes.
        Can be filtered to a specific period or return history for all periods.

        Args:
            period_id (Optional[int]): ID of period to get history for.
                If None, returns history for all periods.

        Returns:
            List[Dict]: List of task history records, each containing:
                - id (int): Task ID
                - title (str): Task title
                - status (str): Current task status
                - resource (str): Assigned resource
                - project (str): Project name
                - created_datetime (str): Creation timestamp
                - todo_datetime (str): Time moved to todo
                - inwork_datetime (str): Time work started
                - completed_datetime (str): Completion timestamp
                - period_name (str): Name of associated period
                Returns empty list if no tasks found or on error.
        """
        try:
            if not self.db.conn or not self.db.cursor:
                return []

            query = """
                SELECT
                    t.id,
                    t.title,
                    t.status,
                    t.resource,
                    t.project,
                    t.created_datetime,
                    t.todo_datetime,
                    t.inwork_datetime,
                    t.completed_datetime,
                    p.name as period_name
                FROM tasks t
                LEFT JOIN performance_periods p ON t.period_id = p.id
                WHERE 1=1
            """

            params = []
            if period_id:
                query += " AND t.period_id = ?"
                params.append(period_id)

            self.db.cursor.execute(query, params)

            columns = [
                "id",
                "title",
                "status",
                "resource",
                "project",
                "created_datetime",
                "todo_datetime",
                "inwork_datetime",
                "completed_datetime",
                "period_name",
            ]

            return [dict(zip(columns, row)) for row in self.db.cursor.fetchall()]

        except sqlite3.Error as e:
            print(f"Error getting task history: {e}")
            return []


# ================================================================================
# ================================================================================


class UIComponents:
    """
    Handles creation and management of UI elements for the Kanban Task Manager.

    This class is responsible for creating and managing all graphical user interface
    elements, including the main window, toolbars, tabs, and task cards. It handles
    styling, layout, and visual components while delegating action handling to the
    main application.

    Attributes:
        root (tk.Tk): The root window of the application
        columns (Dict): Dictionary storing references to Kanban board columns
        colors (Dict): Color scheme definitions for UI elements
        refresh_views_callback (Optional[Callable]): Callback for refreshing views
    """

    def __init__(self, root: tk.Tk):
        """
        Initialize the UI Components manager.

        Args:
            root (tk.Tk): The root window of the application
        """

        self.root = root
        self.columns = {}  # Store column references
        self.setup_theme()
        self.setup_main_window()
        self.refresh_views_callback = None  # Will be set by KanbanApp

    # --------------------------------------------------------------------------------

    def setup_theme(self):
        """
        Setup the application theme and styling.

        Configures the application's color scheme, visual theme, and default
        styles. Defines colors for various UI elements and configures ttk
        styles for consistent appearance across the application.
        """

        # Set customtkinter theme
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Define colors
        self.colors = {
            "bg_light": "#F5F7FA",
            "bg_dark": "#E4E7EB",
            "primary": "#3B82F6",
            "secondary": "#64748B",
            "success": "#10B981",
            "warning": "#F59E0B",
            "text": "#1F2937",
            "text_secondary": "#6B7280",
            "border": "#E5E7EB",
        }

        # Configure ttk styles for the notebook
        style = ttk.Style()
        style.configure("TNotebook", background=self.colors["bg_light"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=self.colors["bg_light"],
            padding=[10, 5],
            font=("Helvetica", 18),
        )

    # --------------------------------------------------------------------------------

    def toggle_theme(self):
        """Toggle between light and dark theme"""
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        ctk.set_appearance_mode(self.current_theme)
        self.colors = self.theme_colors[self.current_theme]
        self.theme_label.configure(
            text="🌙" if self.current_theme == "dark" else "🌞"  # Smiling sun with face
        )

    # --------------------------------------------------------------------------------

    def setup_main_window(self):
        """
        Setup the main application window.

        Configures the main window's title, size, and position. The window size
        is calculated based on screen dimensions, and the window is centered on
        the screen. Also sets minimum window size to ensure usability.
        """

        self.root.title("Kanban Task Manager")
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Calculate window size (e.g., 80% of screen size)
        window_width = int(screen_width * 0.25)
        window_height = int(screen_height * 0.55)

        # Calculate center position
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2

        # Set window size and position
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

        # Optionally, set minimum size to prevent window from being too small
        self.root.minsize(800, 600)

        self.root.configure(bg=self.colors["bg_light"])

    # --------------------------------------------------------------------------------

    def create_menu_bar(self, callbacks: Dict) -> tk.Menu:
        """
        Create the application menu bar.

        Creates the main menu bar with File menu options including database
        operations and application exit.

        Args:
            callbacks (Dict): Dictionary containing callback functions for menu actions:
                - new_db: Callback for creating new database
                - open_db: Callback for opening existing database

        Returns:
            tk.Menu: Configured menu bar instance
        """
        menubar = tk.Menu(self.root, font=("Helvetica", 12))  # Main menu font
        self.root.config(menu=menubar)

        # File menu with custom font
        file_menu = tk.Menu(menubar, tearoff=0, font=("Helvetica", 14))  # Submenu font
        menubar.add_cascade(label="File", menu=file_menu, font=("Helvetica", 12))
        file_menu.add_command(label="New Database...", command=callbacks["new_db"])
        file_menu.add_command(label="Open Database...", command=callbacks["open_db"])
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        return menubar

    # --------------------------------------------------------------------------------

    def create_toolbar(
        self, callbacks: Dict
    ) -> Tuple[
        ctk.CTkFrame, ctk.CTkButton, ctk.CTkButton, ctk.CTkOptionMenu, tk.StringVar
    ]:
        """
        Create the main toolbar with control buttons and period selector.

        Creates a toolbar containing buttons for creating periods and tasks,
        as well as a dropdown menu for selecting the active period.

        Args:
            callbacks (Dict): Dictionary containing callback functions:
                - create_period: Callback for period creation
                - create_task: Callback for task creation
                - change_period: Callback for period selection change

        Returns:
            Tuple containing:
                - ctk.CTkFrame: The toolbar frame
                - ctk.CTkButton: Create period button
                - ctk.CTkButton: Create task button
                - ctk.CTkOptionMenu: Sprint selector dropdown
                - tk.StringVar: Variable holding selected period
        """
        toolbar = ctk.CTkFrame(
            self.root,
            fg_color=self.colors["bg_light"],
            corner_radius=12,
            border_width=1,
            border_color=self.colors["border"],
            height=50,  # Set a fixed height
        )
        toolbar.pack(
            fill=tk.X, padx=5, pady=(2, 5)
        )  # Reduce top padding, keep small bottom padding

        # Button configurations
        button_config = {
            "corner_radius": 8,
            "height": 32,
            "font": ("Helvetica", 16),
            "border_width": 1,
        }

        # Create period button
        create_period_btn = ctk.CTkButton(
            toolbar,
            text="Create Sprint",
            command=callbacks["create_period"],
            fg_color=self.colors["primary"],
            **button_config,
        )
        create_period_btn.pack(side=tk.LEFT, padx=5, pady=2)

        # Create task button
        create_task_btn = ctk.CTkButton(
            toolbar,
            text="Create Task",
            command=callbacks["create_task"],
            fg_color=self.colors["secondary"],
            **button_config,
        )
        create_task_btn.pack(side=tk.LEFT, padx=5, pady=2)

        # Sprint selector
        period_var = tk.StringVar()
        period_selector = ctk.CTkOptionMenu(
            toolbar,
            variable=period_var,
            command=callbacks["change_period"],
            fg_color=self.colors["bg_dark"],
            text_color=self.colors["text"],
            button_color=self.colors["primary"],
            button_hover_color=self.colors["secondary"],
            dropdown_fg_color=self.colors["bg_light"],
            dropdown_text_color=self.colors["text"],
            dropdown_hover_color=self.colors["bg_dark"],
            width=200,
            font=("Helvetica", 16),
            dropdown_font=("Helvetica", 16),
        )
        period_selector.pack(side=tk.LEFT, padx=5, pady=2)

        return toolbar, create_period_btn, create_task_btn, period_selector, period_var

    # --------------------------------------------------------------------------------

    def create_notebook(self) -> ttk.Notebook:
        """
        Create the main notebook widget for tab organization.

        Creates and configures a notebook widget that holds the main
        application tabs: Kanban Board, Unassigned Tasks, and Statistics.

        Returns:
            ttk.Notebook: Configured notebook widget for the main application
                          tabs
        """

        style = ttk.Style()
        style.configure(
            "Custom.TNotebook",
            background=self.colors["bg_light"],
            borderwidth=0,
            padding=5,
        )
        style.configure(
            "Custom.TNotebook.Tab",
            background=self.colors["bg_light"],
            padding=[15, 8],
            font=("Arial", 11),
        )

        notebook = ttk.Notebook(self.root, style="Custom.TNotebook")
        notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        return notebook

    # --------------------------------------------------------------------------------

    def create_kanban_board(self, notebook: ttk.Notebook) -> Tuple[ctk.CTkFrame, Dict]:
        """
        Create the Kanban board tab and its columns.

        Creates the main Kanban board interface with Todo, In Progress, and
        Completed columns. Each column is set up to display task cards.

        Args:
            notebook (ttk.Notebook): Parent notebook widget

        Returns:
            Tuple containing:
                - ctk.CTkFrame: Main Kanban board frame
                - Dict: Dictionary of column containers, keyed by column name
        """
        # Store frame references as class attributes
        self.kanban_frame = ctk.CTkFrame(
            notebook, fg_color=self.colors["bg_light"], corner_radius=0
        )
        # Main frame for Kanban board
        kanban_frame = ctk.CTkFrame(
            notebook, fg_color=self.colors["bg_dark"], corner_radius=0
        )
        notebook.add(kanban_frame, text="Kanban Board")

        # Container for columns
        columns_container = ctk.CTkFrame(kanban_frame, fg_color="transparent")
        columns_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create columns
        columns = {}
        for name in ["Todo", "In Progress", "Completed"]:
            column = self.create_kanban_column(columns_container, name)
            columns[name.lower().replace(" ", "_")] = column

        return kanban_frame, columns

    # --------------------------------------------------------------------------------

    def create_kanban_column(self, parent: ctk.CTkFrame, title: str) -> Dict:
        """
        Create a single Kanban column.

        Creates a column for the Kanban board with a header and scrollable
        container for task cards. Each column has a distinct visual style
        and can hold multiple task cards.

        Args:
            parent (ctk.CTkFrame): Parent frame to contain the column
            title (str): Column title (e.g., "Todo", "In Progress", "Completed")

        Returns:
            Dict: Dictionary containing:
                - frame: Column's main frame
                - task_container: Scrollable container for task cards
        """
        # Column frame with shadow effect
        column = ctk.CTkFrame(
            parent,
            fg_color=self.colors["bg_light"],
            corner_radius=12,
            border_width=1,
            border_color=self.colors["border"],
        )
        column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Column header with gradient effect
        header = ctk.CTkFrame(
            column, corner_radius=12, fg_color=self.colors["primary"], height=40
        )
        header.pack(fill=tk.X, padx=2, pady=2)
        header.pack_propagate(False)

        # Header label
        ctk.CTkLabel(
            header, text=title, font=("Arial", 16, "bold"), text_color="white"
        ).pack(expand=True)

        # Task container with scroll
        task_container = ctk.CTkScrollableFrame(
            column, fg_color="transparent", corner_radius=0
        )
        task_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        return {"frame": column, "task_container": task_container}

    # --------------------------------------------------------------------------------
    def create_unassigned_tab(
        self, notebook: ttk.Notebook
    ) -> Tuple[ctk.CTkFrame, ctk.CTkScrollableFrame]:
        """
        Create the tab for displaying unassigned tasks.

        Creates a tab containing a scrollable frame for displaying tasks that
        haven't been assigned to any period yet.

        Args:
            notebook (ttk.Notebook): Parent notebook widget

        Returns:
            Tuple containing:
                - ctk.CTkFrame: Main frame for unassigned tasks tab
                - ctk.CTkScrollableFrame: Scrollable container for task cards
        """
        self.unassigned_frame = ctk.CTkFrame(  # Store reference
            notebook, fg_color=self.colors["bg_light"], corner_radius=0
        )
        notebook.add(self.unassigned_frame, text="Unassigned Tasks")

        container = ctk.CTkScrollableFrame(
            self.unassigned_frame, fg_color="transparent", corner_radius=0
        )
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        return self.unassigned_frame, container

    # --------------------------------------------------------------------------------

    def create_statistics_tab(self, notebook: ttk.Notebook) -> ctk.CTkFrame:
        """
        Create the tab for displaying task statistics.

        Creates a tab for showing various metrics and statistics about tasks,
        including completion times and resource utilization.

        Args:
            notebook (ttk.Notebook): Parent notebook widget

        Returns:
            ctk.CTkFrame: Main frame for statistics display
        """

        self.stats_frame = ctk.CTkFrame(  # Store reference
            notebook, fg_color=self.colors["bg_light"], corner_radius=0
        )
        notebook.add(self.stats_frame, text="Statistics")
        return self.stats_frame

    # --------------------------------------------------------------------------------

    def create_task_card(
        self, parent: ctk.CTkFrame, task: Dict, callbacks: Dict
    ) -> ctk.CTkFrame:
        """
        Create a visual card representing a task.

        Creates a card displaying task information and appropriate action buttons
        based on the task's status. The card includes title, description,
        project info, and resource assignment if available.

        Args:
            parent (ctk.CTkFrame): Parent container for the card
            task (Dict): Task data including:
                - id: Task identifier
                - title: Task title
                - description: Task description
                - status: Current status
                - project: Project name
                - resource: Assigned resource (optional)
            callbacks (Dict): Callback functions for task actions:
                - move_to_todo: For unassigned tasks
                - assign_resource: For todo tasks
                - start_task: For todo tasks
                - complete_task: For in-progress tasks

        Returns:
            ctk.CTkFrame: The created task card
        """
        # Main card frame with shadow
        card = ctk.CTkFrame(
            parent,
            fg_color="white",
            corner_radius=8,
            border_width=1,
            border_color=self.colors["border"],
        )
        card.pack(fill=tk.X, padx=5, pady=5)

        # Content padding
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # Title with primary color accent
        title = ctk.CTkLabel(
            content,
            text=task["title"],
            font=("Helvetica", 18, "bold"),
            text_color=self.colors["text"],
            anchor="w",
        )
        title.pack(fill=tk.X, pady=(0, 8))

        # Description with secondary text color
        desc = ctk.CTkLabel(
            content,
            text=(
                task["description"][:50] + "..."
                if len(task["description"]) > 50
                else task["description"]
            ),
            text_color=self.colors["text_secondary"],
            anchor="w",
            wraplength=300,
        )
        desc.pack(fill=tk.X, pady=(0, 8))

        # Info section with tags
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(fill=tk.X, pady=(0, 8))

        # Project tag
        project_tag = ctk.CTkFrame(
            info_frame, fg_color=self.colors["bg_dark"], corner_radius=4
        )
        project_tag.pack(side=tk.LEFT, padx=(0, 5))

        ctk.CTkLabel(
            project_tag,
            text=f"📁 {task['project']}",
            font=("Helvetica", 13),
            text_color=self.colors["text"],
        ).pack(padx=8, pady=2)

        # Resource tag if assigned
        if task.get("resource"):
            resource_tag = ctk.CTkFrame(
                info_frame, fg_color=self.colors["bg_dark"], corner_radius=4
            )
            resource_tag.pack(side=tk.LEFT, padx=5)

            ctk.CTkLabel(
                resource_tag,
                text=f"👤 {task['resource']}",
                font=("Arial", 11),
                text_color=self.colors["text"],
            ).pack(padx=8, pady=2)

        # Button configurations based on status
        button_config = {
            "corner_radius": 6,
            "height": 32,
            "border_width": 1,
            "font": ("Helvetica", 15),
        }

        # Action buttons
        button_frame = ctk.CTkFrame(content, fg_color="transparent")
        button_frame.pack(fill=tk.X, pady=(8, 0))

        if task["status"] == "unassigned":
            move_btn = ctk.CTkButton(
                button_frame,
                text="Move to Todo",
                command=lambda: callbacks["move_to_todo"](task["id"]),
                fg_color=self.colors["primary"],
                **button_config,
            )
            move_btn.pack(side=tk.LEFT, padx=2)

        elif task["status"] == "todo":
            assign_btn = ctk.CTkButton(
                button_frame,
                text="Assign Resource",
                command=lambda: callbacks["assign_resource"](task["id"]),
                fg_color=self.colors["secondary"],
                **button_config,
            )
            assign_btn.pack(side=tk.LEFT, padx=2)

            start_btn = ctk.CTkButton(
                button_frame,
                text="Start Work",
                command=lambda: callbacks["start_task"](task["id"]),
                fg_color=self.colors["primary"],
                **button_config,
            )
            start_btn.pack(side=tk.LEFT, padx=2)

        elif task["status"] == "inwork":
            complete_btn = ctk.CTkButton(
                button_frame,
                text="Complete",
                command=lambda: callbacks["complete_task"](task["id"]),
                fg_color=self.colors["success"],
                **button_config,
            )
            complete_btn.pack(side=tk.LEFT, padx=2)

        return card

    # --------------------------------------------------------------------------------

    def create_period_dialog(self, callback) -> None:
        """
        Create a dialog for adding a new performance period.

        Displays a modal dialog with inputs for period name and date range.
        The dialog includes validation and proper formatting of dates.

        Args:
            callback: Function to call with period data when saved.
                      Expected signature: callback(name: str, start_date: str,
                      end_date: str)
        """

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Create Performance Sprint")
        dialog.geometry("400x350")
        dialog.configure(fg_color=self.colors["bg_light"])

        # Add padding frame
        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Sprint name
        name_label = ctk.CTkLabel(
            content,
            text="Sprint Name:",
            font=("Helvetica", 14, "bold"),
            text_color=self.colors["text"],
        )
        name_label.pack(pady=(0, 5))

        name_entry = ctk.CTkEntry(
            content,
            height=35,
            font=("Helvetica", 14),
            corner_radius=6,
            border_width=1,
            border_color=self.colors["border"],
        )
        name_entry.pack(fill=tk.X, pady=(0, 15))

        # Date selectors
        start_label = ctk.CTkLabel(
            content,
            text="Start Date:",
            font=("Helvetica", 14, "bold"),
            text_color=self.colors["text"],
        )
        start_label.pack(pady=(0, 5))

        start_date = DateEntry(
            content,
            font=("Helvetica", 14),
            borderwidth=1,
            background=self.colors["primary"],
            foreground="white",
        )
        start_date.pack(fill=tk.X, pady=(0, 15))

        end_label = ctk.CTkLabel(
            content,
            text="End Date:",
            font=("Helvetica", 14, "bold"),
            text_color=self.colors["text"],
        )
        end_label.pack(pady=(0, 5))

        end_date = DateEntry(
            content,
            font=("Helvetica", 14),
            borderwidth=1,
            background=self.colors["primary"],
            foreground="white",
        )
        end_date.pack(fill=tk.X, pady=(0, 20))

        def save_period():
            callback(name_entry.get(), start_date.get(), end_date.get())
            dialog.destroy()

        save_btn = ctk.CTkButton(
            content,
            text="Save Sprting",
            command=save_period,
            height=38,
            corner_radius=8,
            font=("Helvetica", 15, "bold"),
            fg_color=self.colors["primary"],
        )
        save_btn.pack(fill=tk.X, pady=(10, 0))

    # --------------------------------------------------------------------------------

    def create_task_dialog(self, callback) -> None:
        """
        Create a dialog for adding a new task.

        Displays a modal dialog with inputs for task details including
        title, description, and project type.

        Args:
            callback: Function to call with task data when saved.
                      Expected signature: callback(title: str,
                      description: str, project: str)
        """
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Create Task")
        dialog.geometry("500x600")
        dialog.configure(fg_color=self.colors["bg_light"])

        # Add padding frame
        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Task title
        title_label = ctk.CTkLabel(
            content,
            text="Task Title:",
            font=("Helvetica", 14, "bold"),
            text_color=self.colors["text"],
        )
        title_label.pack(pady=(0, 5))

        title_entry = ctk.CTkEntry(
            content,
            height=35,
            font=("Helvetica", 14),
            corner_radius=6,
            border_width=1,
            border_color=self.colors["border"],
        )
        title_entry.pack(fill=tk.X, pady=(0, 15))

        # Task description
        desc_label = ctk.CTkLabel(
            content,
            text="Description:",
            font=("Helvetica", 14, "bold"),
            text_color=self.colors["text"],
        )
        desc_label.pack(pady=(0, 5))

        desc_entry = ctk.CTkTextbox(
            content,
            height=200,
            font=("Helvetica", 14),
            corner_radius=6,
            border_width=1,
            border_color=self.colors["border"],
        )
        desc_entry.pack(fill=tk.X, pady=(0, 15))

        # Project type
        project_label = ctk.CTkLabel(
            content,
            text="Project Type:",
            font=("Helvetica", 14, "bold"),
            text_color=self.colors["text"],
        )
        project_label.pack(pady=(0, 5))

        project_entry = ctk.CTkEntry(
            content,
            height=35,
            font=("Helvetica", 14),
            corner_radius=6,
            border_width=1,
            border_color=self.colors["border"],
        )
        project_entry.pack(fill=tk.X, pady=(0, 20))

        def save_task():
            callback(
                title_entry.get(), desc_entry.get("1.0", tk.END), project_entry.get()
            )
            dialog.destroy()

        save_btn = ctk.CTkButton(
            content,
            text="Create Task",
            command=save_task,
            height=38,
            corner_radius=8,
            font=("Helvetica", 15, "bold"),
            fg_color=self.colors["primary"],
        )
        save_btn.pack(fill=tk.X, pady=(10, 0))

    # --------------------------------------------------------------------------------

    def set_ui_state(self, state: str, elements: Dict) -> None:
        """
        Enable or disable multiple UI elements.

        Updates the state (enabled/disabled) of multiple UI elements at once.

        Args:
            state (str): New state ('normal' or 'disabled')
            elements (Dict): Dictionary of UI elements to update,
                           where each element supports the configure method
        """

        """Enable or disable UI elements"""
        for element in elements.values():
            if hasattr(element, "configure"):
                element.configure(state=state)


# ================================================================================
# ================================================================================


class KanbanApp:
    """
    Main application class that orchestrates all components of the Kanban Task Manager.

    This class serves as the central coordinator for the application, managing the
    interaction between the UI components and the data management classes. It handles
    all high-level operations including database operations, UI state management,
    and view updates.

    Attributes:
        db_manager (DatabaseManager): Manages database operations
        task_manager (TaskManager): Handles task-related operations
        period_manager (SprintManager): Manages performance periods
        stats_manager (StatisticsManager): Handles statistical calculations
        ui (UIComponents): Manages GUI components
        current_period (Optional[str]): Name of currently selected period
    """

    def __init__(self, root: tk.Tk):
        """
        Initialize the Kanban Task Manager application.

        Sets up all manager classes, initializes the UI, and starts with UI
        in disabled state until a database is loaded.

        Args:
            root (tk.Tk): Root window of the application
        """

        # Initialize managers
        self.db_manager = DatabaseManager()
        self.task_manager = TaskManager(self.db_manager)
        self.period_manager = SprintManager(self.db_manager)
        self.stats_manager = StatisticsManager(self.db_manager)

        # Initialize UI
        self.ui = UIComponents(root)

        # Create UI structure
        self.setup_ui()

        # Initialize state
        self.current_period = None

        # Disable UI until database is loaded
        self.set_ui_state("disabled")

    # --------------------------------------------------------------------------------

    def setup_ui(self):
        """
        Setup the main UI structure and callbacks.

        Creates and configures all UI elements including menu bar, toolbar,
        and tabs. Sets up all necessary callback functions for UI interactions.
        """
        # Create menu with callbacks
        self.menu_callbacks = {
            "new_db": self.create_new_database,
            "open_db": self.open_database,
        }
        self.menubar = self.ui.create_menu_bar(self.menu_callbacks)

        # Create toolbar with callbacks
        self.toolbar_callbacks = {
            "create_period": self.show_create_period_dialog,
            "create_task": self.show_create_task_dialog,
            "change_period": self.change_period,
        }
        toolbar_elements = self.ui.create_toolbar(self.toolbar_callbacks)
        (
            self.toolbar,
            self.create_period_btn,
            self.create_task_btn,
            self.period_selector,
            self.period_var,
        ) = toolbar_elements

        # Create notebook and tabs
        self.notebook = self.ui.create_notebook()

        # Create Kanban board
        self.kanban_frame, self.columns = self.ui.create_kanban_board(self.notebook)

        # Create unassigned tasks tab
        self.unassigned_frame, self.unassigned_container = self.ui.create_unassigned_tab(
            self.notebook
        )

        # Create statistics tab
        self.stats_frame = self.ui.create_statistics_tab(self.notebook)

        self.ui.refresh_views_callback = self.refresh_all_views

    # --------------------------------------------------------------------------------

    def create_new_database(self):
        """
        Create a new database file.

        Opens a file dialog for the user to specify the location and name
        of the new database. Creates the database with the required schema
        and enables the UI if successful.

        Effects:
            - Creates a new SQLite database file
            - Enables UI elements on success
            - Shows success/error messages to user
        """
        filename = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
            title="Create New Database",
        )

        if filename:
            if self.db_manager.connect(filename):
                if self.db_manager.create_schema():
                    self.set_ui_state("normal")
                    messagebox.showinfo("Success", "New database created successfully!")
                else:
                    messagebox.showerror("Error", "Failed to create database schema")
                    self.set_ui_state("disabled")
            else:
                messagebox.showerror("Error", "Failed to create database")

    # --------------------------------------------------------------------------------

    def open_database(self):
        """
        Open an existing database file and load current period.

        Opens a file dialog for selecting an existing database file, verifies
        its schema, and loads the current period if one exists. Enables the UI
        if the database is successfully opened.

        Effects:
            - Connects to existing database file
            - Loads current period if available
            - Enables UI elements on success
            - Updates all views
            - Shows success/error messages to user
        """
        filename = filedialog.askopenfilename(
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
            title="Open Existing Database",
        )

        if filename:
            if self.db_manager.connect(filename):
                if self.db_manager.verify_schema():
                    self.set_ui_state("normal")

                    # Find and set current period
                    current_period = self.db_manager.get_current_period()
                    if current_period:
                        self.current_period = current_period
                        self.period_var.set(current_period)

                    # Refresh all views
                    self.refresh_all_views()
                    messagebox.showinfo("Success", "Database opened successfully!")
                else:
                    messagebox.showerror("Error", "Invalid database schema")
                    self.set_ui_state("disabled")
            else:
                messagebox.showerror("Error", "Failed to open database")

    # --------------------------------------------------------------------------------

    def show_create_period_dialog(self):
        """
        Show dialog for creating a new period.

        Displays a dialog for entering new period details. On successful
        creation, updates the period selector to include the new period.

        Effects:
            - Creates new period in database
            - Updates period selector dropdown
        """

        def save_period(name, start_date, end_date):
            period_id = self.period_manager.create_period(name, start_date, end_date)
            if period_id:
                self.update_period_selector()

        self.ui.create_period_dialog(save_period)

    def show_create_task_dialog(self):
        """
        Show dialog for creating a new task.

        Displays a dialog for entering new task details. On successful
        creation, updates the unassigned tasks view to show the new task.

        Effects:
            - Creates new task in database
            - Updates unassigned tasks view
        """

        def save_task(title, description, project):
            task_id = self.task_manager.create_task(title, description, project)
            if task_id:
                self.update_unassigned_tasks()

        self.ui.create_task_dialog(save_task)

    def change_period(self, period_name):
        """
        Handle period change in the UI.

        Updates the current period selection and refreshes the Kanban board
        to show tasks for the newly selected period.

        Args:
            period_name (str): Name of the newly selected period

        Effects:
            - Updates current_period attribute
            - Refreshes Kanban board view
        """
        self.current_period = period_name
        self.update_kanban_board()

    def update_period_selector(self):
        """
        Update the period selector dropdown.

        Refreshes the period selector with current list of periods from the
        database. If no period is currently selected and periods exist,
        selects the first available period.

        Effects:
            - Updates period selector options
            - May update current period selection
        """
        periods = self.period_manager.get_all_periods()
        self.period_selector.configure(values=[p["name"] for p in periods])
        if periods and not self.current_period:
            self.current_period = periods[0]["name"]
            self.period_var.set(self.current_period)

    # --------------------------------------------------------------------------------

    def update_kanban_board(self):
        """Update the Kanban board view with current tasks.

        Clears and repopulates all Kanban board columns (todo, in_progress, completed)
        with task cards based on the current period selection. Sets up appropriate
        callbacks for task card interactions including resource assignment, starting
        tasks, and completing tasks.
        """

        # Clear current board
        for column in self.columns.values():
            for widget in column["task_container"].winfo_children():
                widget.destroy()

        if self.current_period:
            period = self.period_manager.get_period_by_name(self.current_period)
            if period:
                tasks = self.task_manager.get_tasks_by_period(period["id"])

                # Create callbacks for task cards
                callbacks = {
                    "assign_resource": self.show_assign_resource_dialog,
                    "start_task": self.start_task,
                    "complete_task": self.complete_task,
                }

                # Sort tasks into columns
                for task in tasks:
                    if task["status"] == "todo":
                        container = self.columns["todo"]["task_container"]
                    elif task["status"] == "inwork":
                        container = self.columns["in_progress"]["task_container"]
                    elif task["status"] == "completed":
                        container = self.columns["completed"]["task_container"]
                    else:
                        continue

                    self.ui.create_task_card(container, task, callbacks)

    # --------------------------------------------------------------------------------

    def update_unassigned_tasks(self):
        """Update the unassigned tasks view.

        Clears and repopulates the unassigned tasks container with task cards for
        all tasks that haven't been assigned to a period. Sets up callbacks for
        moving tasks to the todo column.
        """
        # Clear current tasks
        for widget in self.unassigned_container.winfo_children():
            widget.destroy()

        # Get unassigned tasks
        tasks = self.task_manager.get_unassigned_tasks()

        # Create callbacks for task cards
        callbacks = {"move_to_todo": self.move_to_todo}

        # Create task cards
        for task in tasks:
            self.ui.create_task_card(self.unassigned_container, task, callbacks)

    # --------------------------------------------------------------------------------

    def update_statistics(self):
        """Update the statistics view with current metrics.

        Clears and recalculates statistics based on the current period selection.
        If a period is selected, calculates and displays metrics specific to that
        period. Otherwise, shows overall statistics.
        """

        # Clear current statistics
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        # Get current period ID if one is selected
        period_id = None
        if self.current_period:
            period = self.period_manager.get_period_by_name(self.current_period)
            if period:
                period_id = period["id"]

        # Calculate metrics
        metrics = self.stats_manager.calculate_task_metrics(period_id)

        # Create statistics display
        if metrics:
            self.create_statistics_display(metrics)

    # --------------------------------------------------------------------------------

    def create_statistics_display(self, metrics):
        """Create and display a statistical summary of task metrics"""
        # Overall metrics
        overall_frame = ctk.CTkFrame(self.stats_frame)
        overall_frame.pack(fill=tk.X, padx=10, pady=10)

        ctk.CTkLabel(
            overall_frame, text="Overall Metrics", font=("Arial", 16, "bold")
        ).pack(pady=5)

        metrics_text = f"""
        Total Tasks: {metrics['total_tasks']}
        Average Time to Start: {metrics['avg_todo_to_inwork']:.2f} hours
        Average Time to Complete: {metrics['avg_inwork_to_complete']:.2f} hours
        Average Total Time: {metrics['avg_total_time']:.2f} hours
        """

        ctk.CTkLabel(overall_frame, text=metrics_text).pack(pady=5)

        # Resource metrics
        if metrics["by_resource"]:
            resource_frame = ctk.CTkFrame(self.stats_frame)
            resource_frame.pack(fill=tk.X, padx=10, pady=10)

            ctk.CTkLabel(
                resource_frame, text="Metrics by Resource", font=("Arial", 16, "bold")
            ).pack(pady=5)

            for resource, data in metrics["by_resource"].items():
                resource_text = f"""
                Resource: {resource}
                Tasks Completed: {data['tasks_completed']}
                Average Completion Time: {data['avg_completion_time']:.2f} hours
                """
                ctk.CTkLabel(resource_frame, text=resource_text).pack(pady=5)

        # Project metrics
        if metrics["by_project"]:
            project_frame = ctk.CTkFrame(self.stats_frame)
            project_frame.pack(fill=tk.X, padx=10, pady=10)

            ctk.CTkLabel(
                project_frame, text="Metrics by Project", font=("Arial", 16, "bold")
            ).pack(pady=5)

            for project, data in metrics["by_project"].items():
                project_text = f"""
                Project: {project}
                Tasks Completed: {data['tasks_completed']}
                Average Completion Time: {data['avg_completion_time']:.2f} hours
                """
                ctk.CTkLabel(project_frame, text=project_text).pack(pady=5)

    # --------------------------------------------------------------------------------

    def move_to_todo(self, task_id):
        """Move a task to the Todo column of the current period.

        Args:
            task_id: The identifier of the task to move

        Verifies that a period is selected before moving the task.
        If successful, updates both the unassigned tasks view and
        the Kanban board to reflect the change.

        Displays an error message if no period is selected.
        """
        if not self.current_period:
            messagebox.showinfo("Select Sprint", "Please select a sprint first.")
            return

        period = self.period_manager.get_period_by_name(self.current_period)
        if period and self.task_manager.move_to_todo(task_id, period["id"]):
            self.update_unassigned_tasks()
            self.update_kanban_board()

    # --------------------------------------------------------------------------------

    def show_assign_resource_dialog(self, task_id):
        """Show dialog for assigning a resource to a task.

        Args:
            task_id: The identifier of the task to assign

        Opens a modal dialog with an entry field for the resource name.
        Upon successful assignment, updates the Kanban board to reflect
        the change and closes the dialog.
        """
        dialog = ctk.CTkToplevel(self.ui.root)
        dialog.title("Assign Resource")
        dialog.geometry("300x150")

        resource_label = ctk.CTkLabel(dialog, text="Resource Name:")
        resource_label.pack(pady=5)

        resource_entry = ctk.CTkEntry(dialog)
        resource_entry.pack(pady=5)

        def save_resource():
            resource = resource_entry.get()
            if self.task_manager.assign_resource(task_id, resource):
                self.update_kanban_board()
                dialog.destroy()

        save_btn = ctk.CTkButton(dialog, text="Save", command=save_resource)
        save_btn.pack(pady=20)

    # --------------------------------------------------------------------------------

    def start_task(self, task_id):
        """Start a task by moving it to the in-progress state.

        Args:
            task_id: The identifier of the task to start

        Updates the Kanban board to reflect the task's new status
        if the operation is successful.
        """
        if self.task_manager.start_task(task_id):
            self.update_kanban_board()

    # --------------------------------------------------------------------------------

    def complete_task(self, task_id):
        """Complete a task by moving it to the completed state.

        Args:
            task_id: The identifier of the task to complete

        Updates both the Kanban board and statistics views to reflect
        the task's completion if the operation is successful.
        """
        if self.task_manager.complete_task(task_id):
            self.update_kanban_board()
            self.update_statistics()

    # --------------------------------------------------------------------------------

    def refresh_all_views(self):
        """Refresh all views in the application.

        Updates all major components of the UI including:
        - Sprint selector
        - Unassigned tasks view
        - Kanban board
        - Statistics view

        Typically called after major state changes that affect multiple views.
        """
        self.update_period_selector()
        self.update_unassigned_tasks()
        self.update_kanban_board()
        self.update_statistics()

    # --------------------------------------------------------------------------------

    def set_ui_state(self, state):
        """Enable or disable UI elements based on the provided state.

        Args:
            state (bool): True to enable elements, False to disable them

        Affects the following UI elements:
        - Create period button
        - Create task button
        - Sprint selector

        Used to prevent user interactions during certain operations or states.
        """
        elements = {
            "create_period_btn": self.create_period_btn,
            "create_task_btn": self.create_task_btn,
            "period_selector": self.period_selector,
        }
        self.ui.set_ui_state(state, elements)


# ================================================================================
# ================================================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = KanbanApp(root)
    root.mainloop()
# ================================================================================
# ================================================================================
# eof
