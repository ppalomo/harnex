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


# --- setting a project up -----------------------------------------------------------

import copy  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
from contextlib import redirect_stderr, redirect_stdout  # noqa: E402

import setup as setup_script  # noqa: E402  (a plugin script, reached by path)

DEFAULT_ANSWERS: dict[str, object] = {
    "project_name": "scratch",
    "profiles": [],
    "sets": ["git", "code", "sdd", "safety", "canary", "language"],
    "features": [],
    "canary": "Hullaballoo!",
    "decision_model": "mock",
    "check_command": "make check",
    "approvals": {"pointer_agents": False, "pointer_claude": False, "adopt": []},
}


@pytest.fixture
def answers() -> dict:
    """The answers a project gives, as the session would hand them to the script."""
    return copy.deepcopy(DEFAULT_ANSWERS)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """An empty project, the state every scenario starts from or builds on."""
    path = tmp_path / "project"
    path.mkdir()
    return path


@pytest.fixture
def setup_run(tmp_path: Path, plugin_root: Path):
    """Run the script the way its command line does, and return what it said."""

    def run(verb: str, project: Path, answers: dict, *, as_json: bool = False):
        document = tmp_path / "answers.json"
        document.write_text(json.dumps(answers), encoding="utf-8")
        argv = [
            verb,
            "--answers",
            str(document),
            "--project",
            str(project),
            "--plugin-root",
            str(plugin_root),
        ]
        if as_json:
            argv.append("--json")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = setup_script.main(argv)
        return code, out.getvalue() + err.getvalue()

    return run


def tree(project: Path) -> dict[str, bytes]:
    """Every file in a project, so two states can be compared byte for byte."""
    return {
        str(path.relative_to(project)): path.read_bytes()
        for path in sorted(project.rglob("*"))
        if path.is_file()
    }
