"""Local visibility (docs/PLAN.md C7): nothing `/harnex:setup` writes for a project
reaches that project's own version-control history. `shared` visibility — the default,
and every existing test in `test_setup_answers.py`, `test_setup_survey.py` and
`test_setup_write.py` — is unaffected by any of this.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import apply_loop
import setup
import update
import verify_checks
from conftest import commit_all, tree


def _git(project: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(project), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """An empty project that is also a real git repository, the way local visibility's
    own `.git/info/exclude` requirement needs."""
    project = tmp_path / "project"
    project.mkdir()
    _git(project, "init", "-q")
    _git(project, "config", "user.email", "test@test.com")
    _git(project, "config", "user.name", "test")
    _git(project, "config", "commit.gpgsign", "false")
    return project


def _status(project: Path) -> str:
    """Plain `git status --porcelain`: empty means nothing untracked, nothing modified —
    an ignored path never appears here at all, which is the point."""
    return subprocess.run(
        ["git", "-C", str(project), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _status_ignored(project: Path) -> str:
    """With `--ignored`, so a test can confirm a path is ignored, not merely unlisted."""
    return subprocess.run(
        ["git", "-C", str(project), "status", "--porcelain", "--ignored"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


@pytest.fixture
def local_answers(answers: dict) -> dict:
    document = dict(answers)
    document["visibility"] = "local"
    document["tools"] = ["claude"]
    document["store_id"] = "scratch-store"
    document["store_path"] = "/somewhere/store"
    return document


# --- 1.1 / 1.2: the visibility choice and .harnex/config.yml's own shape ------------


def test_visibility_defaults_to_shared(plugin_root: Path, answers: dict) -> None:
    assert setup.read_answers(json.dumps(answers), plugin_root).visibility == "shared"


def test_visibility_local_is_read(plugin_root: Path, local_answers: dict) -> None:
    read = setup.read_answers(json.dumps(local_answers), plugin_root)
    assert read.visibility == "local"
    assert read.tools == ("claude",)
    assert read.store_id == "scratch-store"


def test_an_unknown_visibility_is_refused(plugin_root: Path, answers: dict) -> None:
    answers["visibility"] = "secret"
    with pytest.raises(setup.SetupError):
        setup.read_answers(json.dumps(answers), plugin_root)


def test_an_unknown_tool_is_refused(plugin_root: Path, local_answers: dict) -> None:
    local_answers["tools"] = ["claude", "gpt"]
    with pytest.raises(setup.SetupError):
        setup.read_answers(json.dumps(local_answers), plugin_root)


def test_tools_without_local_visibility_is_refused(plugin_root: Path, answers: dict) -> None:
    answers["tools"] = ["claude"]
    with pytest.raises(setup.SetupError):
        setup.read_answers(json.dumps(answers), plugin_root)


def test_local_visibility_without_a_store_id_is_refused(
    plugin_root: Path, local_answers: dict
) -> None:
    local_answers["store_id"] = ""
    with pytest.raises(setup.SetupError):
        setup.read_answers(json.dumps(local_answers), plugin_root)


def test_a_store_id_without_local_visibility_is_refused(
    plugin_root: Path, answers: dict
) -> None:
    answers["store_id"] = "scratch-store"
    with pytest.raises(setup.SetupError):
        setup.read_answers(json.dumps(answers), plugin_root)


def test_local_config_round_trips_through_its_own_file(
    plugin_root: Path, local_answers: dict
) -> None:
    read = setup.read_answers(json.dumps(local_answers), plugin_root)
    written = setup.format_local_choices(read)
    parsed = setup.parse_choices(
        written, setup.LOCAL_CHOICES, setup.LOCAL_ANSWER_KEYS, setup.LOCAL_LIST_KEYS
    )
    assert parsed == read.as_local_choices()
    assert setup.format_local_choices(read) == written


def test_harnex_yml_s_own_shape_is_unchanged(plugin_root: Path, answers: dict) -> None:
    """`.harnex.yml` still has exactly its seven keys — decision 11 is not reopened."""
    read = setup.read_answers(json.dumps(answers), plugin_root)
    assert set(read.as_choices()) == set(setup.ANSWER_KEYS)
    assert "visibility" not in read.as_choices()


def _local_plan(
    project: Path,
    plugin_root: Path,
    answers: dict,
    home: Path | None = None,
    *,
    commit: bool = True,
) -> "setup.Plan":
    """Plan the fixture, committed first unless asked not to: setup plans only on a clean
    git working tree (design.md D4), and most checks here are about what it plans there."""
    if commit:
        commit_all(project)
    return setup.build_plan(
        project, plugin_root, setup.read_answers(json.dumps(answers), plugin_root), home=home
    )


def _rerun(answers: dict) -> dict:
    """The answers of a rerun: a recorded store is reused, so no `store_path` is asked
    or passed — one passed anyway is refused (design.md D4's last paragraph)."""
    document = dict(answers)
    document.pop("store_path", None)
    return document


def _step(plan: "setup.Plan", path: str) -> "setup.Step":
    steps = [step for step in plan.steps if step.path == path]
    assert len(steps) == 1, f"{path} appears {len(steps)} times in the plan"
    return steps[0]


# --- 2.1 / 2.2: CLAUDE.local.md, never AGENTS.md or CLAUDE.md ----------------------


def test_claude_local_is_written_agents_and_claude_are_not(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    assert (repo / setup.CLAUDE_LOCAL).is_file()
    assert "@.harnex/rules.md" in (repo / setup.CLAUDE_LOCAL).read_text(encoding="utf-8")
    assert not (repo / setup.AGENTS).exists()
    assert not (repo / setup.CLAUDE).exists()


def test_an_existing_agents_md_is_left_byte_identical(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    original = b"# existing team brief\n"
    (repo / setup.AGENTS).write_bytes(original)
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    assert (repo / setup.AGENTS).read_bytes() == original
    plan = _local_plan(repo, plugin_root, _rerun(local_answers))
    assert _step(plan, setup.AGENTS).action == setup.KEEP


def test_an_existing_claude_md_is_left_byte_identical(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    original = b"@AGENTS.md\n@.harnex/rules.md\n"
    (repo / setup.CLAUDE).write_bytes(original)
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    assert (repo / setup.CLAUDE).read_bytes() == original
    plan = _local_plan(repo, plugin_root, _rerun(local_answers))
    assert _step(plan, setup.CLAUDE).action == setup.KEEP


def test_claude_local_is_excluded_via_git_info_exclude_not_the_project_s_gitignore(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    assert not (repo / ".gitignore").exists()
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    assert not (repo / ".gitignore").exists(), "the project's own ignore file must stay untouched"
    exclude = (repo / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert "CLAUDE.local.md" in exclude.splitlines()


def test_git_status_is_clean_after_a_fresh_local_setup(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    assert _status(repo) == ""


def test_git_status_is_clean_after_local_setup_on_an_existing_team_repo(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    (repo / setup.AGENTS).write_text("# existing team brief\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "existing brief")
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    assert _status(repo) == ""


def test_a_foreign_claude_local_md_is_a_conflict_not_an_overwrite(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    (repo / setup.CLAUDE_LOCAL).write_text("my own notes\n", encoding="utf-8")
    plan = _local_plan(repo, plugin_root, local_answers)
    assert plan.conflicts
    code, _ = setup_run("write", repo, local_answers)
    assert code != 0
    assert (repo / setup.CLAUDE_LOCAL).read_text(encoding="utf-8") == "my own notes\n"


def test_git_exclude_is_idempotent_on_a_second_run(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    before = (repo / ".git" / "info" / "exclude").read_bytes()
    code, _ = setup_run("write", repo, _rerun(local_answers))
    assert code == 0
    assert (repo / ".git" / "info" / "exclude").read_bytes() == before


def test_local_visibility_without_a_git_repository_refuses_to_write(
    project: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    """With no repository, `write` refuses on the clean-tree precondition (design.md D4)
    and writes nothing at all."""
    code, output = setup_run("write", project, local_answers, commit=False)
    assert code != 0
    assert "git init" in output
    assert not (project / setup.CLAUDE_LOCAL).exists()
    assert not (project / setup.HARNEX_IGNORE).exists()
    assert not (project / ".git").exists(), "the script never runs git itself"


# --- C9 4.1: a clean git working tree is a precondition (design.md D4) -------------


@pytest.mark.parametrize("visibility", ["local", "shared"])
@pytest.mark.parametrize("decision_model", ["mock", "jev"])
def test_no_git_repository_is_a_conflict_under_either_visibility(
    project: Path,
    plugin_root: Path,
    answers: dict,
    local_answers: dict,
    setup_run,
    visibility: str,
    decision_model: str,
) -> None:
    """No `git init` step and no pending exclude entries any more: the plan opens with the
    conflict saying to create the repository and commit, and every other path is still
    planned alongside it. No `.env` entry is planned without a repository."""
    document = dict(local_answers if visibility == "local" else answers)
    document["decision_model"] = decision_model
    plan = _local_plan(project, plugin_root, document, commit=False)
    assert (plan.steps[0].path, plan.steps[0].action) == (setup.GIT_DIR, setup.CONFLICT)
    assert setup.RULES in [step.path for step in plan.steps]
    assert "`git init`" in plan.conflicts[0] and "commit" in plan.conflicts[0]
    exclude = [step for step in plan.steps if step.path == setup.GIT_EXCLUDE]
    if visibility == "local":
        assert [step.action for step in exclude] == [setup.CONFLICT]
        # Shared visibility needs a repository too (design.md D4), so it is no way out.
        assert not any("`shared`" in conflict for conflict in plan.conflicts)
    else:
        assert exclude == []
    assert not any(".env" in step.detail for step in plan.steps)

    code, output = setup_run("plan", project, document, commit=False)
    assert code == 1
    assert output.count("Plan for ") == 1
    assert "git init" in output
    assert not (project / ".git").exists(), "planning creates no repository"
    assert not (project / ".env").exists()


def test_write_after_the_person_commits_excludes_every_entry_and_env(
    project: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    """The person creates and commits the repository themselves; setup then plans and
    writes the exclude entries as an ordinary write."""
    local_answers["decision_model"] = "jev"
    code, _ = setup_run("plan", project, local_answers, commit=False)
    assert code == 1
    commit_all(project)  # what the person does, never setup
    code, _ = setup_run("write", project, local_answers, commit=False)
    assert code == 0
    lines = (project / setup.GIT_EXCLUDE).read_text(encoding="utf-8").splitlines()
    for path in (*setup.GIT_EXCLUDE_PATHS, ".env"):
        assert path in lines
    assert _check_ignore(project, ".env")
    assert _check_ignore(project, setup.CLAUDE_LOCAL)
    assert not (project / ".env").exists(), "setup never creates .env"


def test_a_local_rerun_after_a_write_is_not_refused(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    """Everything a `local` setup writes is ignored or excluded, so the tree it leaves is
    still clean and a rerun plans as usual — no commit in between."""
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    assert _status(repo) == ""
    plan = _local_plan(repo, plugin_root, _rerun(local_answers), commit=False)
    assert not plan.conflicts
    assert plan.nothing_to_do
    code, output = setup_run("write", repo, _rerun(local_answers), commit=False)
    assert code == 0 and "Nothing to do" in output


def test_a_shared_rerun_before_the_person_commits_plans_nothing_to_do(
    repo: Path, plugin_root: Path, answers: dict, setup_run
) -> None:
    """Under `shared` what setup wrote is the person's to commit; until they do, the only
    uncommitted paths are the harness's own, which do not count, so a rerun plans
    nothing to do."""
    code, _ = setup_run("write", repo, answers)
    assert code == 0
    assert setup.AGENTS in _status(repo)
    plan = _local_plan(repo, plugin_root, answers, commit=False)
    assert not plan.conflicts
    assert all(step.path != setup.GIT_DIR for step in plan.steps)
    assert plan.nothing_to_do
    code, output = setup_run("write", repo, answers, commit=False)
    assert code == 0 and "Nothing to do" in output


# --- C9 1.2: `.env` joins the exclude list when `jev` is chosen ---------------------


def _check_ignore(project: Path, path: str) -> bool:
    """`git check-ignore` exits 0 exactly when git would ignore the path."""
    return (
        subprocess.run(
            ["git", "-C", str(project), "check-ignore", "-q", path], capture_output=True
        ).returncode
        == 0
    )


@pytest.mark.parametrize("visibility", ["local", "shared"])
def test_jev_excludes_env_without_touching_env_or_gitignore(
    repo: Path,
    plugin_root: Path,
    answers: dict,
    local_answers: dict,
    setup_run,
    tmp_path: Path,
    visibility: str,
) -> None:
    """An existing `.env` has to be ignored already for the tree to be clean (design.md
    D4), so the fixture ignores it through the person's own excludes file — the lowest
    precedence source git reads — and `git check-ignore -v` then shows that after the
    write the match comes from `.git/info/exclude` instead."""
    document = dict(local_answers if visibility == "local" else answers)
    document["decision_model"] = "jev"
    env = b"OPENROUTER_API_KEY=not-a-real-key\n"
    ignore = b"build/\n"
    personal = tmp_path / "personal-excludes"
    personal.write_text(".env\n", encoding="utf-8")
    _git(repo, "config", "core.excludesFile", str(personal))
    (repo / ".env").write_bytes(env)
    (repo / ".gitignore").write_bytes(ignore)
    commit_all(repo)
    assert _status(repo) == ""

    plan = _local_plan(repo, plugin_root, document, commit=False)
    step = _step(plan, setup.GIT_EXCLUDE)
    assert step.data is not None and ".env" in step.detail
    assert any(".env" in n and setup.GIT_EXCLUDE in n for n in plan.notices)

    code, _ = setup_run("write", repo, document, commit=False)
    assert code == 0
    matched = subprocess.run(
        ["git", "-C", str(repo), "check-ignore", "-v", ".env"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert matched.startswith(".git/info/exclude:"), matched
    assert (repo / ".env").read_bytes() == env
    assert (repo / ".gitignore").read_bytes() == ignore


def test_jev_excludes_env_even_before_env_exists(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    local_answers["decision_model"] = "jev"
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    assert not (repo / ".env").exists(), "setup never creates .env"
    assert not (repo / ".gitignore").exists(), "setup never creates .gitignore"
    assert ".env" in (repo / setup.GIT_EXCLUDE).read_text(encoding="utf-8").splitlines()
    assert _check_ignore(repo, ".env")


def test_the_env_notice_says_shared_clones_are_not_protected(
    repo: Path, plugin_root: Path, answers: dict, local_answers: dict
) -> None:
    answers["decision_model"] = "jev"
    shared = "\n".join(_local_plan(repo, plugin_root, answers).notices)
    assert "this clone only" in shared

    local_answers["decision_model"] = "jev"
    local = "\n".join(_local_plan(repo, plugin_root, local_answers).notices)
    assert setup.GIT_EXCLUDE in local
    assert "this clone only" not in local


def test_mock_adds_no_env_entry(
    repo: Path, plugin_root: Path, answers: dict, setup_run
) -> None:
    code, _ = setup_run("write", repo, answers)
    assert code == 0
    assert not (repo / setup.GIT_EXCLUDE).exists() or ".env" not in (
        repo / setup.GIT_EXCLUDE
    ).read_text(encoding="utf-8").splitlines()
    plan = _local_plan(repo, plugin_root, answers)
    assert not any(step.path == setup.GIT_EXCLUDE for step in plan.steps)
    assert not any(".env" in notice for notice in plan.notices)


@pytest.mark.parametrize("visibility", ["local", "shared"])
def test_a_jev_to_mock_change_leaves_the_earlier_env_entry_in_place(
    repo: Path, plugin_root: Path, answers: dict, local_answers: dict, setup_run, visibility: str
) -> None:
    """The exclude list is the repository's own: switching away from `jev` neither adds
    the entry again nor takes back the one an earlier run added."""
    document = dict(local_answers if visibility == "local" else answers)
    document["decision_model"] = "jev"
    code, _ = setup_run("write", repo, document)
    assert code == 0
    before = (repo / setup.GIT_EXCLUDE).read_bytes()
    assert ".env" in before.decode("utf-8").splitlines()

    document = _rerun(document)
    document["decision_model"] = "mock"
    plan = _local_plan(repo, plugin_root, document)
    assert not any(".env" in notice for notice in plan.notices)
    exclude_steps = [step for step in plan.steps if step.path == setup.GIT_EXCLUDE]
    assert all(step.data is None and ".env" not in step.detail for step in exclude_steps)

    code, _ = setup_run("write", repo, document)
    assert code == 0
    assert (repo / setup.GIT_EXCLUDE).read_bytes() == before
    assert _check_ignore(repo, ".env")


def test_shared_jev_differs_from_before_only_by_the_env_exclude_step(
    repo: Path, plugin_root: Path, answers: dict, tmp_path: Path
) -> None:
    """`shared` visibility's one deliberate addition: in a git repository, `jev` adds the
    `.git/info/exclude` step for `.env` and its notice, and nothing else. Every project
    setup plans for is now a git repository (design.md D4), so "before" is the same
    project with `mock`: the only other difference is `.harnex.yml` recording the choice."""
    answers["decision_model"] = "jev"
    jev = _local_plan(repo, plugin_root, answers, home=tmp_path / "home")
    answers["decision_model"] = "mock"
    mock = _local_plan(repo, plugin_root, answers, home=tmp_path / "home")

    def shape(plan: "setup.Plan") -> list[tuple]:
        return [
            (step.path, step.owner, step.action, step.detail)
            + ((step.data,) if step.path != setup.CHOICES else ())
            for step in plan.steps
            if step.path != setup.GIT_EXCLUDE
        ]

    assert shape(jev) == shape(mock)
    assert not any(step.path == setup.GIT_EXCLUDE for step in mock.steps)
    exclude = _step(jev, setup.GIT_EXCLUDE)
    assert exclude.data is not None
    original = (repo / setup.GIT_EXCLUDE).read_bytes()  # what `git init` itself wrote
    assert exclude.data.startswith(original)
    added = exclude.data[len(original):].decode("utf-8").splitlines()
    assert [line for line in added if line and not line.startswith("#")] == [".env"]
    assert not jev.conflicts and not mock.conflicts
    assert len(jev.notices) == 1 and mock.notices == []


def test_a_fresh_clone_of_a_shared_jev_project_restores_only_state_and_env(
    repo: Path, plugin_root: Path, answers: dict, setup_run, tmp_path: Path
) -> None:
    """A real `git clone` carries every committed path, but not `.harnex/state/` (it
    ignores itself) and not the `.env` entry (`.git/info/exclude` is never cloned). The
    clone is recognised from the committed record, nothing is asked, and those two are
    the only steps that are not unchanged."""
    answers["decision_model"] = "jev"
    code, _ = setup_run("write", repo, answers, home=tmp_path / "home")
    assert code == 0
    commit_all(repo)

    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "-q", str(repo), str(clone)], check=True, capture_output=True
    )
    assert not (clone / ".harnex" / "state").exists()
    assert ".env" not in (clone / setup.GIT_EXCLUDE).read_text(encoding="utf-8")

    plan = _local_plan(clone, plugin_root, answers, home=tmp_path / "home", commit=False)
    assert not plan.conflicts
    # `keep` is how a path already pointing at the rules, or the project's own record,
    # is reported unchanged: left alone, nothing written.
    moved = [
        (step.path, step.action)
        for step in plan.steps
        if step.action not in (setup.UNCHANGED, setup.KEEP)
    ]
    assert sorted(moved) == sorted(
        [(setup.STATE_IGNORE, setup.CREATE), (setup.GIT_EXCLUDE, setup.UPDATE)]
    )
    assert sorted(step.path for step in plan.writes) == sorted(
        [setup.STATE_IGNORE, setup.GIT_EXCLUDE]
    )
    exclude = _step(plan, setup.GIT_EXCLUDE)
    original = (clone / setup.GIT_EXCLUDE).read_bytes()
    assert exclude.data is not None and exclude.data.startswith(original)
    added = exclude.data[len(original):].decode("utf-8").splitlines()
    assert [line for line in added if line and not line.startswith("#")] == [".env"]


def test_an_update_in_a_fresh_clone_of_a_jev_project_restores_the_env_entry(
    repo: Path, plugin_root: Path, answers: dict, setup_run, tmp_path: Path
) -> None:
    """`update` reads only what is committed and is handed no answers at all, so it asks
    nothing; in a fresh clone of a shared `jev` project it restores the runtime state
    location and the `.env` entry in the clone's own exclude list, and nothing else."""
    answers["decision_model"] = "jev"
    code, _ = setup_run("write", repo, answers, home=tmp_path / "home")
    assert code == 0
    commit_all(repo)

    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "-q", str(repo), str(clone)], check=True, capture_output=True
    )
    assert not _check_ignore(clone, ".env")
    committed = {path: data for path, data in tree(clone).items()}

    report, ok = update.run_update(clone, plugin_root, home=tmp_path / "home")
    assert ok, report
    assert "Conflicts" not in report
    assert (clone / setup.STATE_IGNORE).is_file()
    assert ".env" in (clone / setup.GIT_EXCLUDE).read_text(encoding="utf-8").splitlines()
    assert _check_ignore(clone, ".env")
    assert not (clone / ".env").exists(), "update never creates .env"
    after = tree(clone)
    assert sorted(set(after) - set(committed)) == [setup.STATE_IGNORE]
    assert all(after[path] == data for path, data in committed.items())


def test_the_shared_env_exclude_step_is_owned_by_this_clone(
    repo: Path, plugin_root: Path, answers: dict, local_answers: dict
) -> None:
    """Under `shared` the `.env` entry protects this clone alone, and its step says so;
    under `local` the exclude step stays `local`, like every other local path."""
    answers["decision_model"] = "jev"
    shared = _local_plan(repo, plugin_root, answers)
    assert _step(shared, setup.GIT_EXCLUDE).owner == "this clone"
    rendered = setup.render_plan(shared)
    line = next(line for line in rendered.splitlines() if setup.GIT_EXCLUDE in line)
    assert "this clone" in line

    local_answers["decision_model"] = "jev"
    local = _local_plan(repo, plugin_root, local_answers)
    assert _step(local, setup.GIT_EXCLUDE).owner == "local"


# --- C9 5.1: the repository is found through git (design.md D4) --------------------


@pytest.mark.parametrize("visibility", ["local", "shared"])
def test_a_worktree_excludes_env_in_its_repository_s_own_list(
    repo: Path,
    plugin_root: Path,
    answers: dict,
    local_answers: dict,
    setup_run,
    tmp_path: Path,
    visibility: str,
) -> None:
    """A worktree's `.git` is a file; its exclude list is the common directory's, which
    lies outside the worktree, so the step names it by its absolute path."""
    commit_all(repo)
    worktree = tmp_path / "worktree"
    _git(repo, "worktree", "add", "-q", str(worktree))
    assert (worktree / ".git").is_file()
    document = dict(local_answers if visibility == "local" else answers)
    document["decision_model"] = "jev"

    plan = _local_plan(worktree, plugin_root, document, commit=False)
    assert not plan.conflicts
    exclude = [step for step in plan.steps if step.path.endswith("info/exclude")]
    assert len(exclude) == 1 and Path(exclude[0].path).is_absolute()

    code, _ = setup_run("write", worktree, document, commit=False)
    assert code == 0
    common = Path(git_path(worktree, "info/exclude"))
    assert ".env" in common.read_text(encoding="utf-8").splitlines()
    assert _check_ignore(worktree, ".env")
    if visibility == "local":
        assert _status(worktree) == ""


@pytest.mark.parametrize("visibility", ["local", "shared"])
def test_a_subdirectory_excludes_env_in_the_parent_repository_s_list(
    repo: Path,
    plugin_root: Path,
    answers: dict,
    local_answers: dict,
    setup_run,
    visibility: str,
) -> None:
    """A project in a subdirectory uses the parent's repository: the tree is checked
    there, scoped to the project, and the entries are anchored to the project's own path
    so they exclude its files and nothing beside them."""
    project = repo / "packages" / "app"
    project.mkdir(parents=True)
    (project / "README.md").write_text("mine\n", encoding="utf-8")
    commit_all(repo)
    document = dict(local_answers if visibility == "local" else answers)
    document["decision_model"] = "jev"

    code, _ = setup_run("write", project, document, commit=False)
    assert code == 0
    lines = (repo / setup.GIT_EXCLUDE).read_text(encoding="utf-8").splitlines()
    assert "packages/app/.env" in lines
    assert _check_ignore(project, ".env")
    assert not _check_ignore(repo, ".env"), "only the project's own .env is excluded"
    assert not (project / ".git").exists()
    if visibility == "local":
        assert _status(repo) == ""


def test_a_subdirectory_checks_only_its_own_subtree(
    repo: Path, plugin_root: Path, answers: dict
) -> None:
    project = repo / "app"
    project.mkdir()
    (project / "README.md").write_text("mine\n", encoding="utf-8")
    commit_all(repo)
    (repo / "elsewhere.txt").write_text("not the project's\n", encoding="utf-8")
    plan = _local_plan(project, plugin_root, answers, commit=False)
    assert not plan.conflicts

    (project / "README.md").write_text("changed\n", encoding="utf-8")
    plan = _local_plan(project, plugin_root, answers, commit=False)
    assert plan.steps[0].path == setup.GIT_DIR
    assert plan.conflicts[0].splitlines()[1:] == ["     M README.md"]


def test_a_non_english_locale_still_reports_no_repository(
    project: Path, plugin_root: Path, answers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Git's messages are read under `LC_ALL=C` (design.md D5), so a person whose locale
    is not English still gets "not a git repository" rather than a git failure. Every git
    call setup makes carries `LC_ALL=C`, whatever the person's own environment says."""
    for name in ("LANG", "LC_ALL", "LC_MESSAGES", "LANGUAGE"):
        monkeypatch.setenv(name, "de_DE.UTF-8")
    environments = []
    real_run = subprocess.run

    def recording_run(*args, **kwargs):
        environments.append(kwargs.get("env"))
        return real_run(*args, **kwargs)

    monkeypatch.setattr(setup.subprocess, "run", recording_run)
    repository = setup.find_repository(project)
    assert (repository.found, repository.failure) == (False, "")

    plan = _local_plan(project, plugin_root, answers, commit=False)
    assert plan.steps[0].path == setup.GIT_DIR
    assert plan.steps[0].detail == "not a git repository"
    assert environments and all(env and env["LC_ALL"] == "C" for env in environments)


def git_path(project: Path, path: str) -> str:
    """Where git itself says a path inside the repository's own directory lies."""
    out = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "--path-format=absolute", "--git-path", path],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return out


# --- 3.1 / 3.2: .harnex/ widens its own self-ignore under local visibility ---------


def test_every_path_under_harnex_is_untracked(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    assert (repo / ".harnex" / "config.yml").is_file()
    assert (repo / ".harnex" / "rules.md").is_file()
    assert (repo / ".harnex" / "manifest.json").is_file()
    assert "!! .harnex/" in _status_ignored(repo)
    assert _status(repo) == ""


def test_shared_visibility_s_state_ignore_is_unaffected(
    project: Path, plugin_root: Path, answers: dict, setup_run
) -> None:
    code, _ = setup_run("write", project, answers)
    assert code == 0
    assert (project / setup.STATE_IGNORE).read_text(encoding="utf-8") == setup.STATE_IGNORE_BODY
    assert not (project / setup.HARNEX_IGNORE).exists()


# --- 4.1: the floor goes to .claude/settings.local.json ----------------------------


def test_the_floor_goes_to_settings_local_json(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    assert (repo / setup.SETTINGS_LOCAL).is_file()
    assert not (repo / setup.SETTINGS).exists()
    local = json.loads((repo / setup.SETTINGS_LOCAL).read_text(encoding="utf-8"))
    assert local["permissions"]["ask"] or local["permissions"]["deny"]


def test_an_existing_settings_json_is_byte_identical_after_local_setup(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    original = b'{\n  "permissions": {"allow": ["Bash(ls)"]}\n}\n'
    (repo / setup.SETTINGS).parent.mkdir(parents=True)
    (repo / setup.SETTINGS).write_bytes(original)
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    assert (repo / setup.SETTINGS).read_bytes() == original


# --- 4.2: no .mcp.json write under local visibility ---------------------------------


def test_mcp_is_never_written_under_local_visibility(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    local_answers["profiles"] = ["react"]
    plan = _local_plan(repo, plugin_root, local_answers)
    step = _step(plan, setup.MCP_CONFIG)
    assert step.data is None
    assert "claude mcp add playwright --scope local" in "\n".join(plan.notices)
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    assert not (repo / setup.MCP_CONFIG).exists()


# --- 5.1 / 5.2: the local OpenSpec store id is recorded and reused -----------------


def test_the_store_id_is_recorded_in_local_config(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    text = (repo / setup.LOCAL_CHOICES).read_text(encoding="utf-8")
    assert "store_id: scratch-store" in text


def test_a_store_path_is_read_and_planned_as_a_registration(
    repo: Path, plugin_root: Path, local_answers: dict
) -> None:
    read = setup.read_answers(json.dumps(local_answers), plugin_root)
    assert read.store_path == "/somewhere/store"
    plan = _local_plan(repo, plugin_root, local_answers)
    step = _step(plan, "openspec store")
    assert step.action == setup.REGISTER
    assert step.data is None
    assert step.detail.startswith("register store `scratch-store` at `/somewhere/store`")


def test_a_first_local_setup_without_a_store_path_is_refused(
    repo: Path, plugin_root: Path, local_answers: dict
) -> None:
    local_answers["store_path"] = ""
    with pytest.raises(setup.SetupError) as refusal:
        _local_plan(repo, plugin_root, local_answers)
    assert "store_path" in str(refusal.value)


def test_a_rerun_with_a_recorded_store_id_needs_no_store_path(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    local_answers["store_path"] = ""
    plan = _local_plan(repo, plugin_root, local_answers)
    assert _step(plan, "openspec store").action == setup.UNCHANGED


def test_a_rerun_reuses_the_store_without_a_store_path_answer_at_all(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    """The rerun asks nothing about the store: with no `store_path` key in the answers,
    `plan` and `write` both succeed, nothing is registered and the id stays recorded."""
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    del local_answers["store_path"]
    code, output = setup_run("plan", repo, local_answers)
    assert code == 0
    assert "register store" not in output
    plan = _local_plan(repo, plugin_root, local_answers)
    assert not any(step.action == setup.REGISTER for step in plan.steps)
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    assert "store_id: scratch-store" in (repo / setup.LOCAL_CHOICES).read_text(encoding="utf-8")


def test_a_store_path_is_not_recorded_and_registers_nothing(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    assert "/somewhere/store" not in (repo / setup.LOCAL_CHOICES).read_text(encoding="utf-8")
    assert not Path("/somewhere/store").exists()


def test_the_store_notice_names_only_the_commands_that_actually_use_a_store(
    repo: Path, plugin_root: Path, local_answers: dict
) -> None:
    """`explore` and `review` never touch `openspec`; the plan's own transparency line
    about the store must not claim otherwise — the exact wording a prior /harnex:verify
    pass caught drifting out of sync in docs/PLAN.md and in this template's own comment."""
    plan = _local_plan(repo, plugin_root, local_answers)
    step = _step(plan, "openspec store")
    assert "propose/apply/verify/ship" in step.detail
    assert "explore" not in step.detail
    assert "review" not in step.detail

    template_text = (plugin_root / "context" / "templates" / "local-config.yml").read_text(
        encoding="utf-8"
    )
    assert "propose/apply/verify/ship" in template_text
    assert "explore" not in template_text


def test_a_second_run_keeps_the_recorded_store_id_even_if_a_different_one_is_passed(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    other = _rerun(local_answers)
    other["store_id"] = "a-different-store"
    code, _ = setup_run("write", repo, other)
    assert code == 0
    text = (repo / setup.LOCAL_CHOICES).read_text(encoding="utf-8")
    assert "store_id: scratch-store" in text
    assert "a-different-store" not in text


# --- C9 7.1: a store registered by an interrupted run (design.md D5) --------------


def _registered(answers: dict) -> dict:
    """The answers when the skill finds the store already registered under the id: the
    id, no path, and the flag."""
    document = dict(answers)
    document.pop("store_path", None)
    document["store_registered"] = True
    return document


def test_an_interrupted_registration_completes_through_store_registered(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    """The store was registered and the run stopped before `write`: no id is recorded.
    The plan reuses the store instead of refusing or registering it again, and `write`
    records the id; a rerun after that is the ordinary one."""
    document = _registered(local_answers)
    assert not (repo / setup.LOCAL_CHOICES).exists()
    plan = _local_plan(repo, plugin_root, document)
    step = _step(plan, "openspec store")
    assert step.action == setup.REUSE
    assert step.data is None
    assert step.detail.startswith("reuse store `scratch-store`")
    assert not any(step.action == setup.REGISTER for step in plan.steps)
    assert not plan.conflicts and not plan.nothing_to_do

    code, output = setup_run("write", repo, document)
    assert code == 0, output
    assert "register store" not in output
    text = (repo / setup.LOCAL_CHOICES).read_text(encoding="utf-8")
    assert "store_id: scratch-store" in text
    assert "store_registered" not in text, "an answer of this run only, never recorded"

    plan = _local_plan(repo, plugin_root, _rerun(local_answers), commit=False)
    assert _step(plan, "openspec store").action == setup.UNCHANGED
    assert plan.nothing_to_do


def test_store_registered_with_a_store_path_is_refused(
    plugin_root: Path, local_answers: dict
) -> None:
    local_answers["store_registered"] = True
    with pytest.raises(setup.SetupError) as refusal:
        setup.read_answers(json.dumps(local_answers), plugin_root)
    assert "store_path" in str(refusal.value)


def test_store_registered_under_shared_visibility_is_refused(
    plugin_root: Path, answers: dict
) -> None:
    answers["store_registered"] = True
    with pytest.raises(setup.SetupError) as refusal:
        setup.read_answers(json.dumps(answers), plugin_root)
    assert "store_registered" in str(refusal.value)


def test_store_registered_must_be_a_boolean(plugin_root: Path, local_answers: dict) -> None:
    document = _registered(local_answers)
    document["store_registered"] = "yes"
    with pytest.raises(setup.SetupError):
        setup.read_answers(json.dumps(document), plugin_root)


# --- 7.1 / 7.2: the one-time global settings offer ----------------------------------


def test_the_global_offer_is_shown_but_not_written_without_a_yes(
    repo: Path, plugin_root: Path, local_answers: dict, tmp_path: Path, setup_run
) -> None:
    home = tmp_path / "home"
    plan = _local_plan(repo, plugin_root, local_answers, home=home)
    assert any("instructionFiles" in notice for notice in plan.notices)
    code, _ = setup_run("write", repo, local_answers, home=home)
    assert code == 0
    assert not (home / ".claude" / "settings.json").exists()


def test_the_global_offer_writes_only_after_explicit_yes(
    repo: Path, plugin_root: Path, local_answers: dict, tmp_path: Path, setup_run
) -> None:
    home = tmp_path / "home"
    local_answers["approvals"]["global_instructions"] = True
    code, _ = setup_run("write", repo, local_answers, home=home)
    assert code == 0
    written = json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert (
        written["pluginConfigs"]["agents-md@builtin"]["options"]["instructionFiles"]
        == "claude-md-and-agents-md"
    )


_GLOBAL_KEY = '`pluginConfigs."agents-md@builtin".options.instructionFiles`'
_GLOBAL_VALUE = '"claude-md-and-agents-md"'


def _global_step(plan, home: Path):
    label = str(home / ".claude" / "settings.json")
    matches = [step for step in plan.steps if step.path == label]
    assert len(matches) == 1
    return matches[0]


def test_an_unapproved_global_setting_is_a_plan_line_naming_key_and_value_and_not_written(
    repo: Path, plugin_root: Path, local_answers: dict, tmp_path: Path, setup_run
) -> None:
    home = tmp_path / "home"
    plan = _local_plan(repo, plugin_root, local_answers, home=home)
    step = _global_step(plan, home)
    assert step.action == setup.KEEP
    assert _GLOBAL_KEY in step.detail
    assert _GLOBAL_VALUE in step.detail
    assert "global_instructions" in step.detail
    assert "not on the plan's yes" in step.detail
    assert step.data is None
    assert any("instructionFiles" in notice for notice in plan.notices)
    code, _ = setup_run("write", repo, local_answers, home=home)
    assert code == 0
    assert not (home / ".claude" / "settings.json").exists()


def test_an_approved_global_setting_is_a_plan_line_naming_key_and_value_and_written(
    repo: Path, plugin_root: Path, local_answers: dict, tmp_path: Path, setup_run
) -> None:
    home = tmp_path / "home"
    local_answers["approvals"]["global_instructions"] = True
    plan = _local_plan(repo, plugin_root, local_answers, home=home)
    step = _global_step(plan, home)
    assert step.action == setup.MERGE
    assert _GLOBAL_KEY in step.detail
    assert _GLOBAL_VALUE in step.detail
    code, _ = setup_run("write", repo, local_answers, home=home)
    assert code == 0
    written = json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert (
        written["pluginConfigs"]["agents-md@builtin"]["options"]["instructionFiles"]
        == "claude-md-and-agents-md"
    )


def test_the_global_offer_is_never_made_under_shared_visibility(
    project: Path, plugin_root: Path, answers: dict, tmp_path: Path, setup_run
) -> None:
    home = tmp_path / "home"
    answers["approvals"]["global_instructions"] = True
    code, _ = setup_run("write", project, answers, home=home)
    assert code == 0
    assert not (home / ".claude" / "settings.json").exists()


def test_declining_the_global_offer_leaves_home_settings_untouched_and_repeats(
    repo: Path, plugin_root: Path, local_answers: dict, tmp_path: Path, setup_run
) -> None:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    original = b'{\n  "theme": "dark"\n}\n'
    (home / ".claude" / "settings.json").write_bytes(original)

    code, _ = setup_run("write", repo, local_answers, home=home)
    assert code == 0
    assert (home / ".claude" / "settings.json").read_bytes() == original

    plan_again = _local_plan(repo, plugin_root, _rerun(local_answers), home=home)
    assert any("instructionFiles" in notice for notice in plan_again.notices)


def test_an_already_correct_global_setting_is_recognised_and_left_alone(
    repo: Path, plugin_root: Path, local_answers: dict, tmp_path: Path, setup_run
) -> None:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    already = {
        "pluginConfigs": {"agents-md@builtin": {"options": {"instructionFiles": "claude-md-and-agents-md"}}}
    }
    (home / ".claude" / "settings.json").write_text(json.dumps(already), encoding="utf-8")
    before = (home / ".claude" / "settings.json").read_bytes()

    plan = _local_plan(repo, plugin_root, local_answers, home=home)
    assert not any("instructionFiles" in notice for notice in plan.notices)
    code, _ = setup_run("write", repo, local_answers, home=home)
    assert code == 0
    assert (home / ".claude" / "settings.json").read_bytes() == before


# --- 8.1: the manifest is written, read, and never committed -----------------------


def test_the_manifest_exists_but_is_never_committed(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    record = json.loads((repo / setup.MANIFEST).read_text(encoding="utf-8"))
    assert setup.RULES in record["paths"]
    assert setup.CLAUDE_LOCAL in record["paths"]
    assert "!! .harnex/" in _status_ignored(repo)
    assert _status(repo) == ""


def test_a_second_run_is_nothing_to_do(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    plan = _local_plan(repo, plugin_root, _rerun(local_answers))
    assert plan.nothing_to_do


def test_a_store_path_with_a_recorded_store_id_is_refused(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    """A rerun that still carries a store path would plan a second registration; it is
    refused instead, and nothing is written."""
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    with pytest.raises(setup.SetupError) as refusal:
        _local_plan(repo, plugin_root, local_answers)
    assert "store_path" in str(refusal.value) and "scratch-store" in str(refusal.value)
    before = (repo / setup.LOCAL_CHOICES).read_bytes()
    code, output = setup_run("write", repo, local_answers)
    assert code == 1 and "store_path" in output
    assert (repo / setup.LOCAL_CHOICES).read_bytes() == before


@pytest.mark.parametrize(
    "inside",
    ["{project}", "{project}/store", "{project}/sub/../store", ".", "store", "./sub/store"],
)
def test_a_store_path_inside_the_project_is_refused(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run, inside: str
) -> None:
    """Registering a store inside the project would create an `openspec/` directory in
    it. A relative path is read against the project root, and the root itself counts."""
    local_answers["store_path"] = inside.format(project=repo)
    with pytest.raises(setup.SetupError) as refusal:
        _local_plan(repo, plugin_root, local_answers)
    assert "inside the project's own directory" in str(refusal.value)
    before = tree(repo)
    code, output = setup_run("write", repo, local_answers)
    assert code == 1 and "inside the project's own directory" in output
    assert tree(repo) == before


def test_a_store_path_under_the_home_directory_is_expanded_before_the_check(
    repo: Path, plugin_root: Path, local_answers: dict, monkeypatch
) -> None:
    monkeypatch.setenv("HOME", str(repo))
    local_answers["store_path"] = "~/store"
    with pytest.raises(setup.SetupError) as refusal:
        _local_plan(repo, plugin_root, local_answers)
    assert "inside the project's own directory" in str(refusal.value)


def test_a_store_path_beside_the_project_is_planned(
    repo: Path, plugin_root: Path, local_answers: dict
) -> None:
    """A sibling whose name merely starts with the project's is outside it."""
    local_answers["store_path"] = str(repo.parent / (repo.name + "-store"))
    step = _step(_local_plan(repo, plugin_root, local_answers), "openspec store")
    assert step.action == setup.REGISTER


def test_a_registration_alone_is_work_to_do(repo: Path) -> None:
    """A plan whose only effect is registering the store is not "nothing to do"."""
    plan = setup.Plan(
        project=repo,
        steps=[setup.Step("openspec store", "local", setup.REGISTER, "register store")],
    )
    assert not plan.writes and not plan.conflicts
    assert not plan.nothing_to_do


# --- 6.1 / 6.2: the guided question list, stated in the setup skill ----------------


def _setup_skill_text(plugin_root: Path) -> str:
    return (plugin_root / "skills" / "setup" / "SKILL.md").read_text(encoding="utf-8")


def test_the_codex_notice_says_apply_hands_codex_the_rules() -> None:
    text = setup.CODEX_LOCAL_NOTICE
    assert "`/harnex:apply`" in text
    assert "`.harnex/rules.md`" in text
    assert "outside apply will not have them" in text
    assert "`AGENTS.md` is never written under local visibility" in text
    assert "cannot see this project's rules" not in text


def test_the_skill_states_the_codex_limitation_when_codex_is_chosen(plugin_root: Path) -> None:
    text = " ".join(_setup_skill_text(plugin_root).split())  # wrapping-insensitive
    assert "codex" in text.lower()
    assert "the apply loop (`/harnex:apply`) hands Codex the rules" in text
    assert "`.harnex/rules.md`" in text
    assert "Codex used outside apply will not have them" in text
    assert "AGENTS.md" in text
    assert "cannot see this project's rules" not in text


def test_the_skill_asks_where_the_store_lives_and_proposes_no_path(plugin_root: Path) -> None:
    text = " ".join(_setup_skill_text(plugin_root).split())
    assert "**Store location** (`local` visibility only) — asked only when no store id is recorded" in text
    assert "propose no path of your own" in text
    assert "never adopt the one the `openspec` tool suggests" in text
    assert '"store_id": "", "store_path": ""' in text
    assert "leave `store_path` empty, and do not ask where the store lives" in text


def test_the_skill_reuses_a_store_already_registered_under_its_id(plugin_root: Path) -> None:
    text = " ".join(_setup_skill_text(plugin_root).split())
    question = text[text.find("**Store location**") : text.find("## 3. Local visibility")]
    assert (
        "asked only when no store id is recorded and no store is already registered under "
        "the id setup would use" in question
    )
    assert "step 3 says how to choose that id and look it up" in question
    section = text[text.find("## 3. Local visibility") : text.find("## 4. Show the plan")]
    listing = section.find("openspec store list --json")
    reuse = section.find("reuse it: put the id in `store_id`, leave `store_path` empty")
    asked = section.find("the person's answer to the store location question")
    assert -1 < listing < reuse < asked
    assert '{"stores": [{"id": …, "root": …}, …]}' in section
    assert "a run interrupted after registering the store and before writing" in section
    assert "do not ask where the store lives or register it again" in section
    # The reuse is passed to the script as `store_registered`, and only then.
    flagged = section.find("set `store_registered` to `true`")
    assert reuse < flagged < asked
    assert "A `store_id` already recorded needs neither `store_path` nor `store_registered`." in section
    example = text[text.find("## 4. Show the plan") : text.find("## 5. Approvals")]
    assert '"store_id": "", "store_path": "", "store_registered": false' in example
    assert (
        "`store_registered` is `true` only when the store list held the id and no "
        "`store_id` is recorded; the script refuses it alongside a `store_path`"
    ) in example
    report = text[text.find("## 6. Run the plan's own commands") :]
    assert "say the store was reused, not registered" in report
    # Listing is read-only: no store is registered before the plan's yes.
    assert "openspec store setup" not in section


def test_the_skill_registers_the_store_only_after_the_plan_s_yes_and_never_runs_git_init(
    plugin_root: Path,
) -> None:
    text = " ".join(_setup_skill_text(plugin_root).split())
    plan = text.find("## 4. Show the plan")
    run = text.find("## 6. Run the plan's own commands, then write")
    assert -1 < plan < run
    # Nothing registers a store before the plan is shown.
    assert "openspec store setup" not in text[:plan]
    after_yes = text[run:]
    register = after_yes.find("`openspec store setup <id> --path <path>`")
    write = after_yes.find('setup.py" write')
    assert -1 < register < write
    assert "`openspec store setup` before the person's yes to the plan that shows it" in text
    # The skill never runs `git init` itself: it is only ever something the person does.
    assert "run `git init` in the project root" not in text
    assert "`git init`, if you ran it." not in text
    never = text[text.find("## What this skill never does") :]
    assert "Run `git init`, commit or stash" in never


def test_the_skill_reads_porcelain_paths_unquoted(plugin_root: Path) -> None:
    """Without `-z`, git quotes a path with a space or a non-ASCII character, and the
    prefix is no longer at the front of it."""
    text = " ".join(_setup_skill_text(plugin_root).split())
    check = text[: text.find('setup.py" choices')]
    assert "git status --porcelain=v1 -z --untracked-files=all -- ." in check
    assert "`-z` is what makes that stripping safe" in check
    assert "a space or a non-ASCII character" in check
    assert "ended by a NUL byte" in check
    assert "the original path" in check


def test_the_store_question_says_a_path_inside_the_project_is_refused(
    plugin_root: Path,
) -> None:
    text = " ".join(_setup_skill_text(plugin_root).split())
    question = text[text.find("**Store location**") : text.find("## 3. Local visibility")]
    assert "outside the project's own directory" in question
    assert "the script refuses a path inside it" in question


def test_the_skill_checks_the_clean_tree_before_asking_any_question(plugin_root: Path) -> None:
    text = " ".join(_setup_skill_text(plugin_root).split())
    status = text.find("git status --porcelain=v1 -z --untracked-files=all -- .")
    choices = text.find('setup.py" choices')
    questions = text.find("## 2. Ask, in this order")
    assert -1 < status < choices < questions
    check = text[status:choices]
    assert "If `git rev-parse` fails, there is no repository" in check
    assert "tell the person to run `git init` and commit first" in check
    assert "a worktree and a project in a subdirectory of a repository both work" in check
    prefix = check.find("git rev-parse --show-prefix")
    assert prefix != -1
    assert "relative to the repository's root, not the project's" in check
    assert "strip the prefix `git rev-parse --show-prefix` printed" in check
    assert "empty at the top of a repository" in check
    strip = check.find("strip the prefix")
    assert strip < check.find("The harness's own paths do not count")
    assert "The harness's own paths do not count" in check
    for path in (
        "`AGENTS.md`",
        "`CLAUDE.md`",
        "`.harnex.yml`",
        "`.harnex/`",
        "`openspec/config.yaml`",
        "`.claude/settings.json`",
        "`.mcp.json`",
        "`CLAUDE.local.md`",
        "`.claude/settings.local.json`",
    ):
        assert path in check, f"{path} is missing from the paths that do not count"
    assert "a rerun before the person commits what setup wrote" in check
    assert "If the command lists any other path, stop" in check
    assert "say to commit or stash them first" in check
    assert "An untracked `.env` is the common case" in check
    assert "`.git/info/exclude`" in check
    assert "you do not do it for them here" in check
    assert "Setup never runs `git init`, commits or stashes" in check
    assert "The script's own conflict is what enforces it" in check


def test_the_skill_shows_one_plan_and_asks_one_yes(plugin_root: Path) -> None:
    text = " ".join(_setup_skill_text(plugin_root).split())
    assert "It is the one plan for the whole run" in text
    assert "`.env` among them when `jev` is chosen" in text
    assert "single yes to it covers them. There is no second plan." in text
    assert "do not plan again and do not ask again" in text


def test_the_skill_s_final_report_names_every_side_effect(plugin_root: Path) -> None:
    text = " ".join(_setup_skill_text(plugin_root).split())
    report = text[text.find("every side effect beyond them, by name") :]
    assert "The store registration — its id and its path" in report
    assert "`.env` added to `.git/info/exclude`" in report
    assert '`pluginConfigs."agents-md@builtin".options.instructionFiles`' in report
    assert '`"claude-md-and-agents-md"`' in report


def test_the_skill_asks_the_full_fixed_list_plus_tools(plugin_root: Path) -> None:
    text = _setup_skill_text(plugin_root)
    items = (
        "Project name",
        "Visibility",
        "Rule sets",
        "Profiles",
        "Canary word",
        "Decision backend",
        "Check command",
        "Tools",
        "Store location",
    )
    positions = []
    for item in items:
        needle = f"**{item}"
        position = text.find(needle)
        assert position != -1, f"{item!r} is missing from the guided question list"
        positions.append(position)
    assert positions == sorted(positions), (
        f"the guided question list is out of its claimed order: {items}"
    )


# --- 8.1 (update.py): `update` reads `.harnex/config.yml` the same way setup wrote it --


def test_update_reads_local_config_round_tripped_through_the_template(
    plugin_root: Path, local_answers: dict
) -> None:
    answers = setup.read_answers(json.dumps(local_answers), plugin_root)
    rendered = setup.render_template(
        plugin_root, "local-config.yml", {"keys": setup.format_local_choices(answers).rstrip("\n")}
    )
    round_tripped = update.read_local_choices(rendered, plugin_root)
    assert round_tripped.visibility == "local"
    assert round_tripped.tools == ("claude",)
    assert round_tripped.store_id == "scratch-store"
    assert round_tripped.project_name == answers.project_name


def test_read_recorded_choices_prefers_local_config_when_both_absent_shared(
    repo: Path, plugin_root: Path
) -> None:
    with pytest.raises(setup.SetupError) as refusal:
        update.read_recorded_choices(repo, plugin_root)
    assert "setup" in str(refusal.value).lower()


def test_read_recorded_choices_reads_local_config(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    answers = update.read_recorded_choices(repo, plugin_root)
    assert answers.visibility == "local"
    assert answers.store_id == "scratch-store"


def test_update_run_refreshes_a_local_visibility_project_without_touching_claude_local_md(
    repo: Path, plugin_root: Path, local_answers: dict, tmp_path: Path, setup_run
) -> None:
    home = tmp_path / "home"
    code, _ = setup_run("write", repo, local_answers, home=home)
    assert code == 0
    before = (repo / setup.CLAUDE_LOCAL).read_bytes()

    report, ok = update.run_update(repo, plugin_root, home)
    assert ok
    assert "Nothing to do" in report or "nothing to do" in report.lower()
    assert (repo / setup.CLAUDE_LOCAL).read_bytes() == before
    assert _status(repo) == ""


def test_update_run_re_renders_rules_after_a_set_change_under_local_visibility(
    repo: Path, plugin_root: Path, local_answers: dict, tmp_path: Path, setup_run
) -> None:
    home = tmp_path / "home"
    code, _ = setup_run("write", repo, local_answers, home=home)
    assert code == 0

    # Simulate the project's own local-config.yml choice changing (hand-edited, the way
    # `.harnex.yml` is already expected to be — update never rewrites the answers file).
    config_path = repo / setup.LOCAL_CHOICES
    changed = update.read_recorded_choices(repo, plugin_root)
    import dataclasses

    changed = dataclasses.replace(changed, sets=("code",), canary="")
    new_body = setup.render_template(
        plugin_root, "local-config.yml", {"keys": setup.format_local_choices(changed).rstrip("\n")}
    )
    config_path.write_text(new_body, encoding="utf-8")
    report, ok = update.run_update(repo, plugin_root, home)
    assert ok
    assert "canary" not in (repo / setup.RULES).read_text(encoding="utf-8")
    assert _status(repo) == ""


# --- 5.2 (apply_loop.py): tasks.md lives in the local store's own root ------------


def test_tasks_md_resolves_against_the_store_root_not_the_project(
    repo: Path, tmp_path: Path
) -> None:
    store_root = tmp_path / "store"
    change_dir = store_root / "openspec" / "changes" / "my-change"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text("- [ ] 1.1 do the thing\n", encoding="utf-8")

    tasks = apply_loop.load_tasks(repo, "my-change", store_root)
    assert [task.id for task in tasks] == ["1.1"]
    assert not (repo / "openspec").exists(), "nothing is ever read from the project itself"

    apply_loop.tick_task(repo, "my-change", "1.1", store_root)
    assert "[x] 1.1" in (change_dir / "tasks.md").read_text(encoding="utf-8")


def test_tasks_md_still_defaults_to_the_project_when_no_store_is_given(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    change_dir = project / "openspec" / "changes" / "my-change"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text("- [ ] 1.1 do the thing\n", encoding="utf-8")
    assert apply_loop.tasks_md_path(project, "my-change") == change_dir / "tasks.md"


# --- verify_checks.py: the check command comes from whichever file is recorded ----


def test_verify_checks_reads_the_check_command_from_local_config(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    text = (repo / setup.LOCAL_CHOICES).read_text(encoding="utf-8")
    assert "check_command: make check" in text

    _git(repo, "commit", "-q", "--allow-empty", "-m", "local setup (everything is ignored)")
    path, facts = verify_checks.run_check(repo, "HEAD", plugin_root)
    assert facts["check_command"] == "make check"
    assert path.is_file()


# --- 5.2: the five commands resolve a local store, where they touch openspec at all ---


def _skill_text(plugin_root: Path, name: str) -> str:
    return (plugin_root / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def test_propose_passes_store_to_every_bare_openspec_call(plugin_root: Path) -> None:
    text = _skill_text(plugin_root, "propose")
    assert text.count("--store") >= 3  # new change, status, instructions


def test_apply_resolves_changes_root_for_apply_loop_and_store_for_openspec_status(
    plugin_root: Path
) -> None:
    text = _skill_text(plugin_root, "apply")
    assert "--changes-root" in text
    assert "--store" in text


def test_verify_resolves_the_change_s_own_root_under_local_visibility(plugin_root: Path) -> None:
    text = _skill_text(plugin_root, "verify")
    assert "store_id" in text
    assert "local" in text.lower()


def test_ship_passes_store_to_archive(plugin_root: Path) -> None:
    text = _skill_text(plugin_root, "ship")
    assert "openspec archive" in text
    assert "--store" in text


def test_explore_and_review_never_mention_a_store_or_changes_root(plugin_root: Path) -> None:
    """None of these skills ever call `openspec`, so there is no store to resolve."""
    for name in ("explore", "review", "idea", "flash"):
        text = _skill_text(plugin_root, name)
        assert "--store" not in text
        assert "--changes-root" not in text
        assert "openspec " not in text


def _apply_codex_bullet(plugin_root: Path) -> str:
    text = _skill_text(plugin_root, "apply")
    start = text.index("- **Codex:**")
    return " ".join(text[start : text.index("- **Human:**", start)].split())


def test_apply_prefixes_the_codex_prompt_with_the_rules_under_local_visibility(
    plugin_root: Path
) -> None:
    bullet = _apply_codex_bullet(plugin_root)
    assert "/codex:rescue --wait" in bullet
    assert "Under `local` visibility" in bullet
    assert "Read `.harnex/rules.md` in this project and follow it." in bullet
    assert bullet.index("follow it.") < bullet.index("then the task's own text")


def test_apply_passes_only_the_task_s_own_text_to_codex_under_shared_visibility(
    plugin_root: Path
) -> None:
    bullet = _apply_codex_bullet(plugin_root)
    assert "under `shared` visibility it is the task's own text and nothing else" in bullet
