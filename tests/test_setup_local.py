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


def test_local_visibility_without_a_git_repository_is_a_conflict(
    project: Path, plugin_root: Path, local_answers: dict, setup_run
) -> None:
    code, output = setup_run("write", project, local_answers)
    assert code != 0
    assert "git" in output.lower()
    assert not (project / setup.CLAUDE_LOCAL).exists()


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


def test_the_skill_states_the_codex_limitation_when_codex_is_chosen(plugin_root: Path) -> None:
    text = " ".join(_setup_skill_text(plugin_root).split())  # wrapping-insensitive
    assert "codex" in text.lower()
    assert "cannot see this project's rules" in text
    assert "AGENTS.md" in text


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
