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
sys.path.insert(0, str(REPO_ROOT / "plugin" / "feedback"))
sys.path.insert(0, str(REPO_ROOT / "plugin" / "feedback" / "canary"))


# --- setting a project up -----------------------------------------------------------

import copy  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
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


def git(project: Path, *args: str) -> subprocess.CompletedProcess:
    """Run git inside a fixture project, never against the repository the checks live in."""
    return subprocess.run(
        ["git", "-C", str(project), *args], check=True, capture_output=True, text=True
    )


def commit_all(project: Path) -> None:
    """Bring a fixture project to what setup requires before it plans (design.md D4): a
    git repository with a clean working tree. Creates the repository if there is none,
    with an identity and signing of its own so the person's global settings never reach
    it, then commits whatever the fixture holds."""
    if not (project / ".git").exists():
        git(project, "init", "-q")
        git(project, "config", "user.email", "test@test.com")
        git(project, "config", "user.name", "test")
        git(project, "config", "commit.gpgsign", "false")
    git(project, "add", "-A")
    git(project, "commit", "-q", "--allow-empty", "--no-verify", "-m", "fixture")


@pytest.fixture
def setup_run(tmp_path: Path, plugin_root: Path):
    """Run the script the way its command line does, and return what it said.

    By default the project is committed first (`commit_all`), since setup only plans on a
    clean git working tree; a check of that precondition itself passes `commit=False`.
    The shipped plugin is the harness unless `plugin_root` names another — a check about
    a profile with a team passes `team_plugin_root`, since the shipped one holds none."""
    shipped = plugin_root

    def run(
        verb: str,
        project: Path,
        answers: dict,
        *,
        as_json: bool = False,
        home: Path | None = None,
        commit: bool = True,
        plugin_root: Path | None = None,
    ):
        if commit:
            commit_all(project)
        document = tmp_path / "answers.json"
        document.write_text(json.dumps(answers), encoding="utf-8")
        argv = [
            verb,
            "--answers",
            str(document),
            "--project",
            str(project),
            "--plugin-root",
            str(plugin_root or shipped),
        ]
        if as_json:
            argv.append("--json")
        if home is not None:
            argv += ["--home", str(home)]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = setup_script.main(argv)
        return code, out.getvalue() + err.getvalue()

    return run


def tree(project: Path) -> dict[str, bytes]:
    """Every file in a project, so two states can be compared byte for byte. The
    repository's own `.git/` is left out: committing a fixture or running `git status`
    moves it, and its initial contents depend on the installed git. A check about
    `.git/info/exclude` reads that file itself."""
    return {
        str(path.relative_to(project)): path.read_bytes()
        for path in sorted(project.rglob("*"))
        if path.is_file() and path.relative_to(project).parts[0] != ".git"
    }


# --- a profile with a team (agent-teams, design.md D1 and D3) -----------------------

# The fixture team: one profile directory with three fragments, each for a real role that
# takes one (a propose-phase role and two review-phase roles), and one single-file profile
# with no team. Neither names a stack: they stand for whatever profiles the harness ships.
TEAM_PROFILE = "alpha"
TEAM_SPECIALISTS = ("api-designer", "reviewer", "security-reviewer")
FLAT_PROFILE = "beta"


def team_agent_paths(profile: str = TEAM_PROFILE) -> list[str]:
    """Where the fixture team's agents land, in the order the plan lists them."""
    return [
        f"{setup_script.AGENTS_DIR}{profile}-{specialist}.md"
        for specialist in sorted(TEAM_SPECIALISTS)
    ]


@pytest.fixture
def team_plugin_root(tmp_path: Path, plugin_root: Path) -> Path:
    """The shipped plugin, copied under `tmp_path` and given the two fixture profiles.

    A copy, not an override: setup finds the roles and the profiles where it always
    does, so what it writes here is exactly what it would write for a shipped team."""
    root = tmp_path / "team-plugin"
    shutil.copytree(plugin_root, root, ignore=shutil.ignore_patterns("__pycache__"))
    profiles = root / "tools" / "profiles"
    team = profiles / TEAM_PROFILE
    team.mkdir()
    (team / "profile.md").write_text(f"# {TEAM_PROFILE}\n\nA stack with a team.\n", encoding="utf-8")
    for specialist in TEAM_SPECIALISTS:
        (team / f"{specialist}.md").write_text(
            f"On {TEAM_PROFILE}, as {specialist}.\n", encoding="utf-8"
        )
    (profiles / f"{FLAT_PROFILE}.md").write_text(
        f"# {FLAT_PROFILE}\n\nA stack with no team.\n", encoding="utf-8"
    )
    return root
