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


# ================================================================================
# ================================================================================


class TaskManager:
    """Manages task-related operations"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    # --------------------------------------------------------------------------------

    def create_task(self, title: str, description: str, project: str) -> Optional[int]:
        """
        Create a new task with validation.

        Args:
            title (str): Task title
            description (str): Task description
            project (str): Project name

        Returns:
            Optional[int]: ID of the created task if successful, None if failed

        Raises:
            KanbanDataError: If task data validation fails
            sqlite3.Error: If database operation fails
        """
        try:
            if not self.db.conn or not self.db.cursor:
                return None

            # Validate task data
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

    # --------------------------------------------------------------------------------

    def move_to_todo(self, task_id: int, period_id: int) -> bool:
        """Move a task to Todo status"""
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

    # --------------------------------------------------------------------------------

    def assign_resource(self, task_id: int, resource: str) -> bool:
        """Assign a resource to a task"""
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

    # --------------------------------------------------------------------------------

    def start_task(self, task_id: int) -> bool:
        """Move task to In Work status"""
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

    # --------------------------------------------------------------------------------

    def complete_task(self, task_id: int) -> bool:
        """Move task to Completed status"""
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

    # --------------------------------------------------------------------------------

    def get_tasks_by_period(self, period_id: int) -> List[Dict]:
        """Get all tasks for a specific period"""
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

    # --------------------------------------------------------------------------------

    def get_unassigned_tasks(self) -> List[Dict]:
        """Get all unassigned tasks"""
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


class PeriodManager:
    """Manages performance periods"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    # --------------------------------------------------------------------------------

    def create_period(self, name: str, start_date: str, end_date: str) -> Optional[int]:
        """Create a new performance period"""
        try:
            if not self.db.conn or not self.db.cursor:
                return None

            self.db.cursor.execute(
                """
                INSERT INTO performance_periods (name, start_date, end_date)
                VALUES (?, ?, ?)
            """,
                (name, start_date, end_date),
            )

            self.db.conn.commit()
            return self.db.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Period creation error: {e}")
            return None

    # --------------------------------------------------------------------------------

    def get_all_periods(self) -> List[Dict]:
        """Get all performance periods"""
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

    # --------------------------------------------------------------------------------

    def get_period_by_name(self, name: str) -> Optional[Dict]:
        """Get a period by its name"""
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
    """Handles statistical calculations and reporting"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    # --------------------------------------------------------------------------------

    def calculate_task_metrics(self, period_id: Optional[int] = None) -> Dict:
        """Calculate various task metrics"""
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

    # --------------------------------------------------------------------------------

    def get_task_history(self, period_id: Optional[int] = None) -> List[Dict]:
        """Get task history for analysis"""
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
    """Handles creation and management of UI elements"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.columns = {}  # Store column references
        self.setup_theme()
        self.setup_main_window()
        self.refresh_views_callback = None  # Will be set by KanbanApp
        # self.root = root
        # self.setup_theme()
        # self.setup_main_window()

    # --------------------------------------------------------------------------------

    def setup_theme(self):
        """Setup the application theme and styling"""
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
        """Setup the main window configuration"""
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

        # self.root.geometry("1200x800")
        # self.root.configure(bg=self.colors['bg_light'])

    # --------------------------------------------------------------------------------

    def create_menu_bar(self, callbacks: Dict) -> tk.Menu:
        """Create the application menu bar"""
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
        """Create the main toolbar"""
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

        # OptionMenu configurations (without border_width)
        # option_config = {"corner_radius": 8, "height": 32, "font": ("Helvetica", 16)}

        # Create period button
        create_period_btn = ctk.CTkButton(
            toolbar,
            text="Create Period",
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

        # Period selector
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
        """Create the main notebook with tabs"""
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
        """Create the Kanban board tab and its columns"""
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
        """Create a single Kanban column"""
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
        """Create the unassigned tasks tab"""
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
        """Create the statistics tab"""
        self.stats_frame = ctk.CTkFrame(  # Store reference
            notebook, fg_color=self.colors["bg_light"], corner_radius=0
        )
        notebook.add(self.stats_frame, text="Statistics")
        return self.stats_frame

    # --------------------------------------------------------------------------------

    def create_task_card(
        self, parent: ctk.CTkFrame, task: Dict, callbacks: Dict
    ) -> ctk.CTkFrame:
        """Create a task card widget"""
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
        """Show dialog for creating a new performance period"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Create Performance Period")
        dialog.geometry("400x350")
        dialog.configure(fg_color=self.colors["bg_light"])

        # Add padding frame
        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Period name
        name_label = ctk.CTkLabel(
            content,
            text="Period Name:",
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
            text="Save Period",
            command=save_period,
            height=38,
            corner_radius=8,
            font=("Helvetica", 15, "bold"),
            fg_color=self.colors["primary"],
        )
        save_btn.pack(fill=tk.X, pady=(10, 0))

    # --------------------------------------------------------------------------------

    def create_task_dialog(self, callback) -> None:
        """Show dialog for creating a new task"""
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

        def save_task():
            callback(
                title_entry.get(), desc_entry.get("1.0", tk.END), project_entry.get()
            )
            dialog.destroy()

        save_btn = ctk.CTkButton(dialog, text="Save", command=save_task)
        save_btn.pack(pady=20)

    # --------------------------------------------------------------------------------

    def set_ui_state(self, state: str, elements: Dict) -> None:
        """Enable or disable UI elements"""
        for element in elements.values():
            if hasattr(element, "configure"):
                element.configure(state=state)


# ================================================================================
# ================================================================================


class KanbanApp:
    """Main application class that orchestrates all components"""

    def __init__(self, root: tk.Tk):
        # Initialize managers
        self.db_manager = DatabaseManager()
        self.task_manager = TaskManager(self.db_manager)
        self.period_manager = PeriodManager(self.db_manager)
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
        """Setup the main UI structure and callbacks"""
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
        """Create a new database file"""
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
        """Open an existing database file and load current period"""
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
        """Show dialog for creating a new period"""

        def save_period(name, start_date, end_date):
            period_id = self.period_manager.create_period(name, start_date, end_date)
            if period_id:
                self.update_period_selector()

        self.ui.create_period_dialog(save_period)

    # --------------------------------------------------------------------------------

    def show_create_task_dialog(self):
        """Show dialog for creating a new task"""

        def save_task(title, description, project):
            task_id = self.task_manager.create_task(title, description, project)
            if task_id:
                self.update_unassigned_tasks()

        self.ui.create_task_dialog(save_task)

    # --------------------------------------------------------------------------------

    def change_period(self, period_name):
        """Handle period change"""
        self.current_period = period_name
        self.update_kanban_board()

    # --------------------------------------------------------------------------------

    def update_period_selector(self):
        """Update the period selector dropdown"""
        periods = self.period_manager.get_all_periods()
        self.period_selector.configure(values=[p["name"] for p in periods])
        if periods and not self.current_period:
            self.current_period = periods[0]["name"]
            self.period_var.set(self.current_period)

    # --------------------------------------------------------------------------------

    def update_kanban_board(self):
        """Update the Kanban board view"""
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
        """Update the unassigned tasks view"""
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
        """Update the statistics view"""
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
        """Create the statistics display"""
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
        """Move a task to the Todo column"""
        if not self.current_period:
            messagebox.showinfo("Select Period", "Please select a period first.")
            return

        period = self.period_manager.get_period_by_name(self.current_period)
        if period and self.task_manager.move_to_todo(task_id, period["id"]):
            self.update_unassigned_tasks()
            self.update_kanban_board()

    # --------------------------------------------------------------------------------

    def show_assign_resource_dialog(self, task_id):
        """Show dialog for assigning a resource"""
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
        """Start a task"""
        if self.task_manager.start_task(task_id):
            self.update_kanban_board()

    # --------------------------------------------------------------------------------

    def complete_task(self, task_id):
        """Complete a task"""
        if self.task_manager.complete_task(task_id):
            self.update_kanban_board()
            self.update_statistics()

    # --------------------------------------------------------------------------------

    def refresh_all_views(self):
        """Refresh all views"""
        self.update_period_selector()
        self.update_unassigned_tasks()
        self.update_kanban_board()
        self.update_statistics()

    # --------------------------------------------------------------------------------

    def set_ui_state(self, state):
        """Enable or disable UI elements"""
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
