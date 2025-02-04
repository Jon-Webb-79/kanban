Welcome to PyKanban documentation! (V0.1.0)
===========================================

Will add documentation here later!

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   Code <Code>

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Contributing
============

Pull requests are welcome. For major changes, please open an issue first to discuss
what you would like to change. Please make sure to include and update tests
as well as relevant doc-string and Sphinx updates.

License
=======

The License is included in the **kanban** package.

Requirements
============

This library is developed and tested on macOS and Arch Linux operating
systems. It is developed with ``Python 3.13.1`` using ``tkinter`` as a
GUI front end. The package is managed using `Poetry <https://python-poetry.org/>`_
as a package manager.

Installation and Build Guide
============================

Getting the Code
----------------

Clone the repository:

.. code-block:: bash

   git clone https://github.com/Jon-Webb-79/kanban.git
   cd kanban

Contribute to Code Base
-----------------------

1. Establish a pull request with the git repository owner.

2. Once the package has been downloaded, you will also need to install
   Python 3.13 or a later version to support documentation with Sphinx.

3. Activate the virtual environment with the following command:

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

4. Install dependencies:

   If using Poetry:

   .. code-block:: bash

      poetry install

   Otherwise, install from ``requirements.txt``:

   .. code-block:: bash

      pip install -r requirements.txt
