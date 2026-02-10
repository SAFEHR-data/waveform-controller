"""Pytest configuration and shared fixtures."""

import os


def pytest_configure(config):
    """Pytest hook: runs once at startup, before test collection.

    Sets INSTANCE_NAME so it is in place before any test module is imported
    (and thus before required settings such as INSTANCE_NAME are read at import time).
    """
    os.environ["INSTANCE_NAME"] = "pytest"
