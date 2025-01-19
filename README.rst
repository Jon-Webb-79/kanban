*******************
kanban Task Manager
*******************

A Python-based desktop application that implements a Kanban-style task management
system with performance period tracking. This application provides a modern,
intuitive interface for managing tasks across different time periods while
maintaining historical data for metrics and analysis.

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. image:: https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336
    :target: https://pycqa.github.io/isort/

.. image:: https://readthedocs.org/projects/flake8/badge/?version=latest
    :target: https://flake8.pycqa.org/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: http://www.mypy-lang.org/static/mypy_badge.svg
   :target: http://mypy-lang.org/

.. image:: https://github.com/Jon-Webb-79/kanban/workflows/Tests/badge.svg?cache=none
    :target: https://github.com/Jon-Webb-79/kanban/actions

Features
########

* Performance Period Management
    - Create and manage distinct time periods for task organization
    - Automatic detection and loading of current performance period
    - Historical period tracking

* Task Management
    - Create and track tasks through their complete lifecycle
    - Move tasks between Unassigned, Todo, In Progress, and Completed states
    - Assign resources to tasks
    - Categorize tasks by project type

* Visual Task Board
    - Kanban-style board with drag-and-drop functionality
    - Clear visual representation of task status
    - Filter tasks by resource or project

* Metrics and Analysis
    - Track task completion times
    - Calculate resource utilization
    - Generate performance metrics by period
    - Historical data retention for trend analysis

Technical Details
#################

Built using:

* Python 3.13
* tkinter/customtkinter for the GUI
* SQLite for data persistence
* pandas for metrics calculation

Contributing
############
Pull requests are welcome.  For major changes, please open an issue first to discuss
what you would like to change.  Please make sure to include and update tests
as well as relevant doc-string and sphinx updates.

License
#######
The License is included in the **kanban** package

Requirements
############
This library is developed and tested on Macintosh and Arch Linux Operating
Systems.  It is developed with ``Python 3.13.1``.  The version of each
package used in this library can be viewed in the ``pyproject.toml`` file.
This library also uses ``poetry 2.0.1`` as a package manager.

Installation
############
In order to download this repository from github, follow these TBD instructions

Contribute to Code Base
-----------------------
#. Establish a pull request with the git repository owner.

#. Once the package has been downloade, you will also need to install
   Python3.13 or later version to support documentation with Sphinx.

#. Navigate to the ``kanban/`` directory.

#. Activate the virtual environment with the following command.

.. table:: Activation Commands for Virtual Environments

   +----------------------+------------------+-------------------------------------------+
   | Platform             | Shell            | Command to activate virtual environment   |
   +======================+==================+===========================================+
   | POSIX                | bash/zsh         | ``$ source <venv>/bin/activate``          |
   +                      +------------------+-------------------------------------------+
   |                      | fish             | ``$ source <venv>/bin/activate.fish``     |
   +                      +------------------+-------------------------------------------+
   |                      | csh/tcsh         | ``$ source <venv>/bin/activate.csh``      |
   +                      +------------------+-------------------------------------------+
   |                      | Powershell       | ``$ <venv>/bin/Activate.ps1``             |
   +----------------------+------------------+-------------------------------------------+
   | Windows              | cmd.exe          | ``C:\> <venv>\\Scripts\\activate.bat``    |
   +                      +------------------+-------------------------------------------+
   |                      | PowerShell       | ``PS C:\\> <venv>\\Scripts\\Activate.ps1``|
   +----------------------+------------------+-------------------------------------------+

#. Install packages to virtual environments from ``requirements.txt`` file

   .. code-block:: bash

      pip install -r requirements.txt

#. At this point you can build the files in the same way described in the
   previous section and contribute to documentation.

Documentation
=============
This code in this repository is further documented at the
XXX website
