"""Shared fixtures for the harness's own checks.

The checks run against the repository they live in, so everything is anchored to the
repository root rather than to the current working directory.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """The repository root, whatever directory pytest was started from."""
    return REPO_ROOT


@pytest.fixture(scope="session")
def plugin_root(repo_root: Path) -> Path:
    """The directory that is installed on a machine."""
    return repo_root / "plugin"


@pytest.fixture(scope="session")
def rules_dir(plugin_root: Path) -> Path:
    """Where pillar 1 keeps the rule sets."""
    return plugin_root / "context" / "rules"


# The scripts are installed beside the pillars, not as an importable package, so the
# checks reach them the way the host will: by path.
sys.path.insert(0, str(REPO_ROOT / "plugin" / "scripts"))
