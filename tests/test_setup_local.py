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


def _local_plan(project: Path, plugin_root: Path, answers: dict, home: Path | None = None) -> "setup.Plan":
    return setup.build_plan(
        project, plugin_root, setup.read_answers(json.dumps(answers), plugin_root), home=home
    )


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
    plan = _local_plan(repo, plugin_root, local_answers)
    assert _step(plan, setup.AGENTS).action == setup.KEEP


def test_an_existing_claude_md_is_left_byte_identical(
    repo: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    original = b"@AGENTS.md\n@.harnex/rules.md\n"
    (repo / setup.CLAUDE).write_bytes(original)
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    assert (repo / setup.CLAUDE).read_bytes() == original
    plan = _local_plan(repo, plugin_root, local_answers)
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
    code, _ = setup_run("write", repo, local_answers)
    assert code == 0
    assert (repo / ".git" / "info" / "exclude").read_bytes() == before


def test_local_visibility_without_a_git_repository_refuses_to_write(
    project: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    """`write` with `git init` still pending refuses outright rather than writing
    everything except the exclude entries (design.md D4)."""
    code, output = setup_run("write", project, local_answers)
    assert code != 0
    assert "git init" in output
    assert not (project / setup.CLAUDE_LOCAL).exists()
    assert not (project / setup.HARNEX_IGNORE).exists()
    assert not (project / ".git").exists(), "the script never runs git itself"


# --- C9 1.3: `git init` is a plan line under local visibility ----------------------


def test_local_visibility_without_a_git_repository_plans_git_init_not_a_conflict(
    project: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    plan = _local_plan(project, plugin_root, local_answers)
    assert not plan.conflicts
    init = _step(plan, setup.GIT_DIR)
    assert init.action == setup.INIT and init.data is None
    exclude = _step(plan, setup.GIT_EXCLUDE)
    assert exclude.action == setup.PENDING and exclude.data is None
    for path in setup.GIT_EXCLUDE_PATHS:
        assert path in exclude.detail
    assert ".env" not in exclude.detail
    assert plan.steps.index(init) < plan.steps.index(exclude)

    code, output = setup_run("plan", project, local_answers)
    assert code == 0
    assert "git init" in output
    assert not (project / ".git").exists(), "planning creates no repository"


def test_jev_with_git_init_pending_plans_the_env_exclusion_in_the_same_plan(
    project: Path, plugin_root: Path, local_answers: dict
) -> None:
    local_answers["decision_model"] = "jev"
    plan = _local_plan(project, plugin_root, local_answers)
    assert not plan.conflicts
    assert _step(plan, setup.GIT_DIR).action == setup.INIT
    exclude = _step(plan, setup.GIT_EXCLUDE)
    assert exclude.action == setup.PENDING and ".env" in exclude.detail
    notices = "\n".join(plan.notices)
    assert "once `git init` has created the repository" in notices
    assert "not a git repository" not in notices


def test_jev_with_git_init_pending_shows_one_plan_with_both_lines(
    project: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    """What the person reads before the single yes: the rendered plan names `git init`
    and the `.env` exclusion together, and nothing has happened yet."""
    local_answers["decision_model"] = "jev"
    code, output = setup_run("plan", project, local_answers)
    assert code == 0
    assert output.count("Plan for ") == 1, "one plan, not a second one after `git init`"
    lines = output.splitlines()
    init = [line for line in lines if "`git init` creates one" in line]
    exclude = [line for line in lines if setup.GIT_EXCLUDE in line and ".env" in line]
    assert len(init) == 1
    assert any(line.strip().startswith(setup.PENDING) for line in exclude)
    assert lines.index(init[0]) < lines.index(exclude[0])
    assert not (project / ".git").exists()
    assert not (project / ".env").exists()


def test_write_after_git_init_excludes_every_entry_and_env(
    project: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    """The skill runs `git init` after the yes; `write`'s own re-survey then finds the
    repository and writes the entries that were pending on it."""
    local_answers["decision_model"] = "jev"
    code, _ = setup_run("plan", project, local_answers)
    assert code == 0
    _git(project, "init", "-q")  # what the skill does after the person's yes
    code, _ = setup_run("write", project, local_answers)
    assert code == 0
    lines = (project / setup.GIT_EXCLUDE).read_text(encoding="utf-8").splitlines()
    for path in (*setup.GIT_EXCLUDE_PATHS, ".env"):
        assert path in lines
    assert _check_ignore(project, ".env")
    assert _check_ignore(project, setup.CLAUDE_LOCAL)
    assert not (project / ".env").exists(), "setup never creates .env"
    rerun = _local_plan(project, plugin_root, local_answers)
    assert not any(step.action == setup.INIT for step in rerun.steps)


@pytest.mark.parametrize("decision_model", ["mock", "jev"])
def test_shared_visibility_without_a_git_repository_is_unchanged(
    project: Path, plugin_root: Path, answers: dict, setup_run, decision_model: str
) -> None:
    """`.git` is never setup's to create under `shared`: no `git init` step, no exclude
    step, and the `.env` notice still says the repository is missing."""
    answers["decision_model"] = decision_model
    plan = _local_plan(project, plugin_root, answers)
    assert not any(step.path in (setup.GIT_DIR, setup.GIT_EXCLUDE) for step in plan.steps)
    assert not any(step.action in (setup.INIT, setup.PENDING) for step in plan.steps)
    if decision_model == "jev":
        assert "not a git repository" in "\n".join(plan.notices)
    code, _ = setup_run("write", project, answers)
    assert code == 0
    assert not (project / ".git").exists()


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
    repo: Path, plugin_root: Path, answers: dict, local_answers: dict, setup_run, visibility: str
) -> None:
    document = dict(local_answers if visibility == "local" else answers)
    document["decision_model"] = "jev"
    env = b"OPENROUTER_API_KEY=not-a-real-key\n"
    ignore = b"build/\n"
    (repo / ".env").write_bytes(env)
    (repo / ".gitignore").write_bytes(ignore)

    plan = _local_plan(repo, plugin_root, document)
    step = _step(plan, setup.GIT_EXCLUDE)
    assert step.data is not None and ".env" in step.detail
    assert any(".env" in n and setup.GIT_EXCLUDE in n for n in plan.notices)

    code, _ = setup_run("write", repo, document)
    assert code == 0
    assert _check_ignore(repo, ".env")
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
    `.git/info/exclude` step for `.env` and nothing else. The same answers in a project
    with no repository are what `shared` with `jev` planned before this change."""
    answers["decision_model"] = "jev"
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    in_repo = _local_plan(repo, plugin_root, answers, home=tmp_path / "home")
    without_repo = _local_plan(elsewhere, plugin_root, answers, home=tmp_path / "home")

    def shape(plan: "setup.Plan") -> list[tuple]:
        return [
            (step.path, step.owner, step.action, step.detail, step.data)
            for step in plan.steps
            if step.path != setup.GIT_EXCLUDE
        ]

    assert shape(in_repo) == shape(without_repo)
    exclude = _step(in_repo, setup.GIT_EXCLUDE)
    assert exclude.data is not None
    original = (repo / setup.GIT_EXCLUDE).read_bytes()  # what `git init` itself wrote
    assert exclude.data.startswith(original)
    added = exclude.data[len(original):].decode("utf-8").splitlines()
    assert [line for line in added if line and not line.startswith("#")] == [".env"]
    assert not in_repo.conflicts and not without_repo.conflicts
    assert len(in_repo.notices) == len(without_repo.notices) == 1

    answers["decision_model"] = "mock"
    mock = _local_plan(repo, plugin_root, answers, home=tmp_path / "home")
    assert [(s.path, s.owner, s.action) for s in mock.steps] == [
        (s.path, s.owner, s.action) for s in in_repo.steps if s.path != setup.GIT_EXCLUDE
    ]


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
    other = dict(local_answers)
    other["store_id"] = "a-different-store"
    code, _ = setup_run("write", repo, other)
    assert code == 0
    text = (repo / setup.LOCAL_CHOICES).read_text(encoding="utf-8")
    assert "store_id: scratch-store" in text
    assert "a-different-store" not in text


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

    plan_again = _local_plan(repo, plugin_root, local_answers, home=home)
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
    plan = _local_plan(repo, plugin_root, local_answers)
    assert plan.nothing_to_do


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
    assert "**Store location** (`local` visibility only, and only when no `store_id` is recorded)" in text
    assert "propose no path of your own" in text
    assert "never adopt the one the `openspec` tool suggests" in text
    assert '"store_id": "", "store_path": ""' in text
    assert "leave `store_path` empty, and do not ask where the store lives" in text


def test_the_skill_runs_git_init_and_the_store_registration_only_after_the_plan_s_yes(
    plugin_root: Path,
) -> None:
    text = " ".join(_setup_skill_text(plugin_root).split())
    plan = text.find("## 4. Show the plan")
    run = text.find("## 6. Run the plan's own commands, then write")
    assert -1 < plan < run
    # Nothing registers a store before the plan is shown.
    assert "openspec store setup" not in text[:plan]
    after_yes = text[run:]
    git_init = after_yes.find("run `git init` in the project root")
    register = after_yes.find("`openspec store setup <id> --path <path>`")
    write = after_yes.find('setup.py" write')
    assert -1 < git_init < register < write
    assert "`git init` before the person's yes to the plan that shows them" in text


def test_the_skill_shows_one_plan_and_asks_one_yes(plugin_root: Path) -> None:
    text = " ".join(_setup_skill_text(plugin_root).split())
    assert "It is the one plan for the whole run" in text
    assert "`.env` among them when `jev` is chosen" in text
    assert "single yes to it covers them. There is no second plan." in text
    assert "do not plan again and do not ask again" in text


def test_the_skill_s_final_report_names_every_side_effect(plugin_root: Path) -> None:
    text = " ".join(_setup_skill_text(plugin_root).split())
    report = text[text.find("every side effect beyond them, by name") :]
    assert "`git init`, if you ran it." in report
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
