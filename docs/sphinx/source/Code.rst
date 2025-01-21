Code Documentation
==================

This section contains the automatically generated API documentation for the
Kanban application.

.. toctree::
   :maxdepth: 2

KanbanDataError
###############
.. autoclass:: kanban.kanban.KanbanDataError
   :members:
   :undoc-members:
   :show-inheritance:

DatabaseManager
###############
.. autoclass:: kanban.kanban.DatabaseManager
   :members:
   :undoc-members:
   :show-inheritance:

Usage Example
-------------
The following example demonstrates how to use the `DatabaseManager` class
to manage the database schema, verify its integrity, and perform operations.

.. code-block:: python

   from kanban.kanban import DatabaseManager, KanbanDataError

   # Create an instance of DatabaseManager
   db_manager = DatabaseManager()

   # Connect to an SQLite database file
   if db_manager.connect("kanban_tasks.db"):
       print("Database connection successful.")

   # Create the schema if it doesn't exist
   if db_manager.create_schema():
       print("Database schema created successfully.")

   # Verify the schema structure
   if db_manager.verify_schema():
       print("Schema verification passed.")
   else:
       print("Schema verification failed.")

   # Insert and validate period data
   try:
       db_manager.validate_period_data("Sprint 1", "01/01/25", "01/15/25")
       print("Valid period data.")
   except KanbanDataError as e:
       print(f"Period validation error: {e}")

   # Insert and validate a task
   try:
       db_manager.validate_task_data("Design UI", "Project A")
       print("Valid task data.")
   except KanbanDataError as e:
       print(f"Task validation error: {e}")

   # Get the current period
   current_period = db_manager.get_current_period()
   if current_period:
       print(f"Current period: {current_period}")
   else:
       print("No active period found.")

   # Close the database connection
   db_manager.close()
   print("Database connection closed.")

TaskManager
###########
.. autoclass:: kanban.kanban.TaskManager
   :members:
   :undoc-members:
   :show-inheritance:

PeriodManager
#############
.. autoclass:: kanban.kanban.PeriodManager
   :members:
   :undoc-members:
   :show-inheritance:

StatisticsManager
#################
.. autoclass:: kanban.kanban.StatisticsManager
   :members:
   :undoc-members:
   :show-inheritance:

UIComponents
############
.. autoclass:: kanban.kanban.UIComponents
   :members:
   :undoc-members:
   :show-inheritance:

KanbanApp
#########
.. autoclass:: kanban.kanban.KanbanApp
   :members:
   :undoc-members:
   :show-inheritance:
