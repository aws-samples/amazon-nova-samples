"""
Root-level conftest.py for pytest configuration.

This file registers command-line options early in the pytest initialization process,
ensuring compatibility with pytest 9.x which validates addopts before loading plugins.
"""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """
    Register command-line options early for pytest 9.x compatibility.
    
    This hook runs before pytest validates the addopts from pyproject.toml,
    ensuring that the --add-nova-act-report option is recognized.
    
    Note: The actual plugin implementation is in pytest-html-nova-act package.
    This is just an early registration to satisfy pytest 9.x config validation.
    We check if the option already exists to avoid conflicts.
    """
    group = parser.getgroup("terminal reporting")
    
    # Only add the option if it hasn't been added yet
    # This prevents conflicts if the plugin has already registered it
    try:
        group.addoption(
            "--add-nova-act-report",
            action="store_true",
            default=False,
            help="Enable adding expandable links to the pytest-html report.",
        )
    except ValueError:
        # Option already exists, which is fine
        pass
