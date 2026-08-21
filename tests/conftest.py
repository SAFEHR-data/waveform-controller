"""Pytest configuration and shared fixtures."""

import os
from pathlib import Path


def _clear_docker_coverage_shards(root: Path) -> None:
    for stale in root.glob(".coverage.docker.*"):
        stale.unlink(missing_ok=True)


def pytest_configure(config):
    """Pytest hook: runs once at startup, before test collection.

    Sets INSTANCE_NAME so it is in place before any test module is imported
    (and thus before required settings such as INSTANCE_NAME are read at import time).
    """
    os.environ["INSTANCE_NAME"] = "pytest"
    # Drop stale in-Docker coverage shards from previous runs (use pytest root, not cwd).
    _clear_docker_coverage_shards(Path(config.rootpath))
