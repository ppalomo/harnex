"""The survey and the plan: what is there, what would happen to it, and what stops it.

Every class in the survey comes from the record and the bytes on disk, never from a
path's mere presence. That is what makes recovery possible without a journal: a file
that is already what the harness would write is recognised as current, whatever the
record says about it.
"""

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest

import render_agents
import setup
from conftest import (
    FLAT_PROFILE,
    TEAM_PROFILE,
    TEAM_SPECIALISTS,
    commit_all,
    git,
    team_agent_paths,
    tree,
)


def _plan(project: Path, plugin_root: Path, answers: dict) -> setup.Plan:
    """Plan the fixture as it stands, committed first: setup only plans on a clean git
    working tree (design.md D4), and these checks are about what it plans there."""
    commit_all(project)
    return _plan_as_is(project, plugin_root, answers)


def _plan_as_is(project: Path, plugin_root: Path, answers: dict) -> setup.Plan:
    return setup.build_plan(
        project, plugin_root, setup.read_answers(json.dumps(answers), plugin_root)
    )


def _step(plan: setup.Plan, path: str) -> setup.Step:
    steps = [step for step in plan.steps if step.path == path]
    assert len(steps) == 1, f"{path} appears {len(steps)} times in the plan"
    return steps[0]


def test_every_path_appears_exactly_once(project: Path, plugin_root: Path, answers) -> None:
    plan = _plan(project, plugin_root, answers)
    paths = [step.path for step in plan.steps]
    assert sorted(paths) == sorted(set(paths))
    assert set(paths) == set(setup.PROJECT_PATHS) | set(setup.HARNESS_PATHS) | {
        setup.SETTINGS,
        setup.MANIFEST,
    }


def test_an_empty_project_is_all_creation(project: Path, plugin_root: Path, answers) -> None:
    plan = _plan(project, plugin_root, answers)
    assert not plan.conflicts
    assert all(step.action == setup.CREATE for step in plan.steps)


def test_planning_writes_nothing(project: Path, plugin_root: Path, answers, setup_run) -> None:
    (project / "README.md").write_text("mine\n", encoding="utf-8")
    before = tree(project)
    code, _ = setup_run("plan", project, answers)
    assert code == 0
    assert tree(project) == before


def test_a_written_project_is_all_keep_and_unchanged(
    project: Path, plugin_root: Path, answers, setup_run
) -> None:
    setup_run("write", project, answers)
    plan = _plan(project, plugin_root, answers)
    assert plan.nothing_to_do
    assert {step.action for step in plan.steps} == {setup.KEEP, setup.UNCHANGED}


def test_a_rendering_that_moved_is_an_update(
    project: Path, plugin_root: Path, answers, setup_run
) -> None:
    setup_run("write", project, answers)
    answers["sets"] = ["git"]
    answers["canary"] = ""
    plan = _plan(project, plugin_root, answers)
    assert _step(plan, setup.RULES).action == setup.UPDATE
    assert "git" in (project / ".harnex" / "rules.md").read_text(encoding="utf-8")


def test_a_harness_file_edited_by_hand_is_a_conflict(
    project: Path, plugin_root: Path, answers, setup_run
) -> None:
    setup_run("write", project, answers)
    (project / setup.RULES).write_text("my own rules\n", encoding="utf-8")
    plan = _plan(project, plugin_root, answers)
    assert _step(plan, setup.RULES).action == setup.CONFLICT
    assert any("edited after the harness wrote it" in c for c in plan.conflicts)
    assert not plan.writes


def test_a_harness_file_with_no_record_at_all_is_a_conflict(
    project: Path, plugin_root: Path, answers
) -> None:
    (project / ".harnex").mkdir()
    (project / setup.RULES).write_text("rules I wrote by hand\n", encoding="utf-8")
    plan = _plan(project, plugin_root, answers)
    assert _step(plan, setup.RULES).action == setup.CONFLICT
    assert any("no record of what the harness generated" in c for c in plan.conflicts)


def test_a_file_already_holding_what_would_be_written_is_current(
    project: Path, plugin_root: Path, answers, setup_run
) -> None:
    """What an interruption leaves: the paths are written, the record is not."""
    setup_run("write", project, answers)
    (project / setup.MANIFEST).unlink()
    plan = _plan(project, plugin_root, answers)
    assert _step(plan, setup.RULES).action == setup.UNCHANGED
    assert not plan.conflicts
    assert [step.path for step in plan.writes] == [setup.MANIFEST]


def test_adoption_turns_a_conflict_into_a_write(
    project: Path, plugin_root: Path, answers
) -> None:
    (project / ".harnex").mkdir()
    (project / setup.RULES).write_text("rules I wrote by hand\n", encoding="utf-8")
    answers["approvals"]["adopt"] = [setup.RULES]
    plan = _plan(project, plugin_root, answers)
    assert _step(plan, setup.RULES).action == setup.ADOPT
    assert not plan.conflicts


def test_every_conflict_is_reported_in_one_run(
    project: Path, plugin_root: Path, answers, setup_run
) -> None:
    setup_run("write", project, answers)
    (project / setup.RULES).write_text("my own rules\n", encoding="utf-8")
    (project / setup.SETTINGS).write_text("{not json", encoding="utf-8")
    plan = _plan(project, plugin_root, answers)
    assert len(plan.conflicts) == 2
    assert {step.path for step in plan.steps if step.action == setup.CONFLICT} == {
        setup.RULES,
        setup.SETTINGS,
    }


def test_a_plan_with_a_conflict_exits_non_zero_and_writes_nothing(
    project: Path, answers, setup_run
) -> None:
    setup_run("write", project, answers)
    (project / setup.RULES).write_text("my own rules\n", encoding="utf-8")
    before = tree(project)
    code, said = setup_run("write", project, answers)
    assert code == 1
    assert "Conflicts" in said
    assert tree(project) == before


@pytest.mark.parametrize(
    "record, says",
    [
        ("{not json", "unreadable"),
        ('{"format": 99, "paths": {}, "entries": {}}', "format 99"),
    ],
)
def test_a_record_the_harness_cannot_read_stops_it(
    project: Path, plugin_root: Path, answers, record: str, says: str
) -> None:
    (project / ".harnex").mkdir()
    (project / setup.MANIFEST).write_text(record, encoding="utf-8")
    with pytest.raises(setup.SetupError) as refusal:
        _plan(project, plugin_root, answers)
    assert says in str(refusal.value)


def test_an_absent_record_is_not_an_error(project: Path, plugin_root: Path, answers) -> None:
    assert setup.read_manifest(project) is None
    assert not _plan(project, plugin_root, answers).conflicts


def test_a_ui_profile_proposes_the_playwright_entry_until_approved(
    project: Path, plugin_root: Path, answers
) -> None:
    answers["profiles"] = ["react"]
    plan = _plan(project, plugin_root, answers)

    step = _step(plan, setup.MCP_CONFIG)
    assert step.action == setup.KEEP and step.data is None
    expected = "\n".join(
        "    " + line
        for line in json.dumps({"mcpServers": {"playwright": setup.PLAYWRIGHT_MCP}}, indent=2).splitlines()
    )
    assert expected in "\n".join(plan.notices)


@pytest.mark.parametrize("profiles", [[], ["fastapi"]])
def test_a_non_ui_profile_never_proposes_or_writes_playwright(
    project: Path, plugin_root: Path, answers, setup_run, profiles: list[str]
) -> None:
    answers["profiles"] = profiles
    assert all(step.path != setup.MCP_CONFIG for step in _plan(project, plugin_root, answers).steps)

    code, _ = setup_run("write", project, answers)
    assert code == 0
    assert not (project / setup.MCP_CONFIG).exists()


def test_a_plausible_frontend_profile_outside_ui_registry_gets_no_playwright_entry(
    project: Path, tmp_path: Path
) -> None:
    plugin_root = tmp_path / "plugin"
    registry = plugin_root / "tools" / "profiles" / "ui.json"
    registry.parent.mkdir(parents=True)
    registry.write_text('["react"]\n', encoding="utf-8")
    answers = setup.Answers(
        project_name="fixture",
        profiles=("svelte",),
        sets=("git",),
        features=(),
        canary="",
        decision_model="mock",
        check_command="true",
    )
    plan = setup.Plan(project)

    owned = setup._plan_mcp(plan, project, plugin_root, answers, None)

    assert owned == {}
    assert all(step.path != setup.MCP_CONFIG for step in plan.steps)


def test_an_existing_playwright_entry_is_left_byte_identical(
    project: Path, plugin_root: Path, answers, setup_run
) -> None:
    answers["profiles"] = ["react"]
    original = b'{\n  "mcpServers": {"playwright": {"command": "custom"}},\n  "project": true\n}\n'
    (project / setup.MCP_CONFIG).write_bytes(original)

    plan = _plan(project, plugin_root, answers)
    step = _step(plan, setup.MCP_CONFIG)
    assert step.action == setup.KEEP
    assert step.detail == 'a different "playwright" entry already exists; left alone'
    code, _ = setup_run("write", project, answers)
    assert code == 0
    assert (project / setup.MCP_CONFIG).read_bytes() == original


def test_a_matching_existing_playwright_entry_is_identified_as_harness_owned(
    project: Path, plugin_root: Path, answers
) -> None:
    answers["profiles"] = ["react"]
    (project / setup.MCP_CONFIG).write_text(
        json.dumps({"mcpServers": {"playwright": setup.PLAYWRIGHT_MCP}}), encoding="utf-8"
    )

    step = _step(_plan(project, plugin_root, answers), setup.MCP_CONFIG)

    assert step.detail == "already carries the Playwright MCP entry"


def test_profile_changes_re_evaluate_playwright_without_removing_it(
    project: Path, plugin_root: Path, answers, setup_run
) -> None:
    setup_run("write", project, answers)
    assert not (project / setup.MCP_CONFIG).exists()

    answers["profiles"] = ["react"]
    assert _step(_plan(project, plugin_root, answers), setup.MCP_CONFIG).action == setup.KEEP
    answers["approvals"]["mcp_playwright"] = True
    code, _ = setup_run("write", project, answers)
    assert code == 0
    before = (project / setup.MCP_CONFIG).read_bytes()
    record = json.loads((project / setup.MANIFEST).read_text(encoding="utf-8"))
    assert record["entries"][setup.MCP_CONFIG] == {"mcpServers": ["playwright"]}

    answers["profiles"] = []
    assert all(step.path != setup.MCP_CONFIG for step in _plan(project, plugin_root, answers).steps)
    code, _ = setup_run("write", project, answers)
    assert code == 0
    assert (project / setup.MCP_CONFIG).read_bytes() == before


def test_update_mode_never_creates_a_missing_project_file(
    project: Path, plugin_root: Path, answers
) -> None:
    plan = setup.build_plan(
        project,
        plugin_root,
        setup.read_answers(json.dumps(answers), plugin_root),
        mode="update",
    )
    step = _step(plan, setup.AGENTS)
    assert step.action == setup.MISSING
    assert step.data is None
    assert any(setup.AGENTS in notice for notice in plan.notices)


def _update_plan(project: Path, plugin_root: Path, answers: dict) -> setup.Plan:
    return setup.build_plan(
        project, plugin_root, setup.read_answers(json.dumps(answers), plugin_root), mode="update"
    )


def _project_writes(plan: setup.Plan) -> list[setup.Step]:
    """Every step an `"update"`-mode plan proposes for a project-owned path that would
    actually write something — the one shape the guarantee says never exists."""
    return [step for step in plan.steps if step.owner == "project" and step.data is not None]


# The general guarantee design.md records for this change: "no Step with owner ==
# 'project' ever carries data is not None when build_plan runs in 'update' mode" — across
# more of the survey's own states than the single missing-everything fixture above covers.
# If 1.1's `mode == "update"` branch is ever reverted or bypassed, the first of these to
# notice is the one with a project file missing, since that is exactly the state in which
# the reverted code would fall back to creating it.


def test_update_mode_writes_no_project_file_when_nothing_is_present(
    project: Path, plugin_root: Path, answers
) -> None:
    plan = _update_plan(project, plugin_root, answers)
    assert _project_writes(plan) == []
    assert all(_step(plan, path).action == setup.MISSING for path in setup.PROJECT_PATHS)


def test_update_mode_writes_no_project_file_when_everything_is_present_and_current(
    project: Path, plugin_root: Path, answers, setup_run
) -> None:
    setup_run("write", project, answers)
    plan = _update_plan(project, plugin_root, answers)
    assert _project_writes(plan) == []
    assert all(_step(plan, path).action == setup.KEEP for path in setup.PROJECT_PATHS)


def test_update_mode_writes_no_project_file_when_one_project_file_is_missing(
    project: Path, plugin_root: Path, answers, setup_run
) -> None:
    setup_run("write", project, answers)
    (project / setup.CHOICES).unlink()
    plan = _update_plan(project, plugin_root, answers)
    assert _project_writes(plan) == []
    assert _step(plan, setup.CHOICES).action == setup.MISSING
    assert all(
        _step(plan, path).action == setup.KEEP
        for path in setup.PROJECT_PATHS
        if path != setup.CHOICES
    )


def test_update_mode_writes_no_project_file_when_a_harness_file_was_edited_by_hand(
    project: Path, plugin_root: Path, answers, setup_run
) -> None:
    """A conflict elsewhere in the plan is no excuse to write a project-owned path: the
    guarantee holds step by step, not only when the rest of the plan is clean."""
    setup_run("write", project, answers)
    (project / setup.RULES).write_text("my own rules\n", encoding="utf-8")
    plan = _update_plan(project, plugin_root, answers)
    assert _project_writes(plan) == []
    assert _step(plan, setup.RULES).action == setup.CONFLICT
    assert plan.conflicts


def test_the_env_notice_appears_only_when_jev_is_chosen(
    project: Path, plugin_root: Path, answers
) -> None:
    answers["decision_model"] = "jev"
    plan = _plan(project, plugin_root, answers)
    assert any(".env" in notice and "OPENROUTER_API_KEY=" in notice for notice in plan.notices)
    assert ".env" in setup.render_plan(plan)
    assert "OPENROUTER_API_KEY=" in setup.render_plan(plan)
    assert ".env" in setup.plan_as_json(plan)
    assert "OPENROUTER_API_KEY=" in setup.plan_as_json(plan)

    answers["decision_model"] = "mock"
    plan = _plan(project, plugin_root, answers)
    assert not any(".env" in notice for notice in plan.notices)
    assert ".env" not in setup.render_plan(plan)
    assert ".env" not in setup.plan_as_json(plan)


# --- the clean-tree precondition (design.md D4) -------------------------------------


def _refused(plan: setup.Plan) -> str:
    """The conflict a failed precondition leaves: first in the plan, alongside every
    other path, which is still planned and printed (design.md D4)."""
    assert (plan.steps[0].path, plan.steps[0].action) == (setup.GIT_DIR, setup.CONFLICT)
    assert [step.path for step in plan.steps].count(setup.GIT_DIR) == 1
    assert setup.RULES in [step.path for step in plan.steps], "the rest is still planned"
    assert setup.RULES in setup.render_plan(plan)
    return plan.conflicts[0]


@pytest.mark.parametrize("visibility", ["shared", "local"])
def test_a_project_with_no_repository_is_a_conflict(
    project: Path, plugin_root: Path, answers, setup_run, tmp_path: Path, visibility: str
) -> None:
    if visibility == "local":
        answers.update(visibility="local", store_id="scratch", store_path=str(tmp_path / "s"))
    (project / "README.md").write_text("mine\n", encoding="utf-8")
    conflict = _refused(_plan_as_is(project, plugin_root, answers))
    assert "not a git repository" in conflict
    assert "`git init`" in conflict and "commit" in conflict

    before = tree(project)
    code, said = setup_run("write", project, answers, commit=False, home=tmp_path / "home")
    assert code == 1 and "Conflicts" in said
    assert tree(project) == before
    assert not (project / ".git").exists(), "setup never creates the repository"


@pytest.mark.parametrize("visibility", ["shared", "local"])
def test_a_modified_file_is_a_conflict_listing_it(
    project: Path, plugin_root: Path, answers, setup_run, tmp_path: Path, visibility: str
) -> None:
    if visibility == "local":
        answers.update(visibility="local", store_id="scratch", store_path=str(tmp_path / "s"))
    (project / "README.md").write_text("mine\n", encoding="utf-8")
    commit_all(project)
    (project / "README.md").write_text("changed\n", encoding="utf-8")
    head = git(project, "rev-parse", "HEAD").stdout

    conflict = _refused(_plan_as_is(project, plugin_root, answers))
    assert "README.md" in conflict
    assert "commit or stash" in conflict

    before = tree(project)
    code, said = setup_run("write", project, answers, commit=False, home=tmp_path / "home")
    assert code == 1 and "README.md" in said
    assert tree(project) == before
    assert git(project, "rev-parse", "HEAD").stdout == head, "setup never commits"
    assert git(project, "stash", "list").stdout == "", "setup never stashes"


def test_an_untracked_file_is_a_conflict_listing_it(
    project: Path, plugin_root: Path, answers
) -> None:
    commit_all(project)
    (project / "notes").mkdir()
    (project / "notes" / "draft.md").write_text("new\n", encoding="utf-8")
    conflict = _refused(_plan_as_is(project, plugin_root, answers))
    assert "notes/draft.md" in conflict, "every untracked file is listed, not its directory"


def test_an_ignored_file_does_not_count(project: Path, plugin_root: Path, answers) -> None:
    (project / ".gitignore").write_text("build/\n", encoding="utf-8")
    commit_all(project)
    (project / "build").mkdir()
    (project / "build" / "out.bin").write_bytes(b"\0")
    plan = _plan_as_is(project, plugin_root, answers)
    assert not plan.conflicts
    assert plan.writes


def test_a_clean_repository_plans_as_usual(project: Path, plugin_root: Path, answers) -> None:
    (project / "README.md").write_text("mine\n", encoding="utf-8")
    commit_all(project)
    plan = _plan_as_is(project, plugin_root, answers)
    assert not plan.conflicts
    assert all(step.path != setup.GIT_DIR for step in plan.steps)


def test_a_failing_git_is_a_conflict(project: Path, plugin_root: Path, answers) -> None:
    """A `.git` git cannot read is not a tree anyone can call clean."""
    (project / ".git").write_text("gitdir: /nowhere\n", encoding="utf-8")
    conflict = _refused(_plan_as_is(project, plugin_root, answers))
    # git's own wording of the failure varies by version (some print the gitdir, some
    # `(null)`), so only setup's part of the message is asserted.
    assert "`git` failed" in conflict and "make `git status` work" in conflict


def test_a_dirty_project_path_conflicts_and_the_harness_s_own_do_not(
    project: Path, plugin_root: Path, answers
) -> None:
    """Only a path that is not the harness's own counts against the tree, and the
    conflict lists that path alone while the plan still shows every other one."""
    (project / "README.md").write_text("mine\n", encoding="utf-8")
    commit_all(project)
    (project / "README.md").write_text("changed\n", encoding="utf-8")
    (project / setup.AGENTS).write_text("# half-written by an earlier run\n", encoding="utf-8")
    (project / setup.CHOICES).write_text("project_name: scratch\n", encoding="utf-8")

    plan = _plan_as_is(project, plugin_root, answers)
    conflict = _refused(plan)
    listed = conflict.splitlines()[1:]
    assert [line.split()[-1] for line in listed] == ["README.md"]
    rendered = setup.render_plan(plan)
    for path in (*setup.PROJECT_PATHS, *setup.HARNESS_PATHS, setup.SETTINGS, setup.MANIFEST):
        assert path in rendered


def test_update_on_a_dirty_tree_is_not_refused(
    project: Path, plugin_root: Path, answers
) -> None:
    (project / "README.md").write_text("mine\n", encoding="utf-8")
    commit_all(project)
    (project / "README.md").write_text("changed\n", encoding="utf-8")
    (project / "untracked.txt").write_text("new\n", encoding="utf-8")
    plan = _update_plan(project, plugin_root, answers)
    assert all(step.path != setup.GIT_DIR for step in plan.steps)
    assert not any("not clean" in conflict for conflict in plan.conflicts)


def test_update_mode_does_not_check_the_tree(project: Path, plugin_root: Path, answers) -> None:
    """Under `update` a shared project's harness-owned files may be uncommitted."""
    (project / "README.md").write_text("mine\n", encoding="utf-8")
    plan = _update_plan(project, plugin_root, answers)
    assert all(step.path != setup.GIT_DIR for step in plan.steps)


# --- the chosen profiles' agents (agent-teams, design.md D3) -------------------------


def _agent_steps(plan: setup.Plan) -> list[setup.Step]:
    return [step for step in plan.steps if step.path.startswith(setup.AGENTS_DIR)]


def test_a_profile_with_a_team_plans_one_line_per_agent_naming_the_profile(
    project: Path, team_plugin_root: Path, answers
) -> None:
    answers["profiles"] = [TEAM_PROFILE]
    plan = _plan(project, team_plugin_root, answers)
    rendered = render_agents.render([TEAM_PROFILE], team_plugin_root)
    steps = _agent_steps(plan)
    assert [step.path for step in steps] == team_agent_paths() == list(rendered)
    for step in steps:
        assert (step.owner, step.action) == ("harness", setup.CREATE)
        assert TEAM_PROFILE in step.detail, "the line says which profile's team it is"
        assert step.data == rendered[step.path], "the renderer's own bytes, untouched"
    assert plan.steps[-1].path == setup.MANIFEST, "the record is still written last"
    assert not plan.conflicts


def test_a_flat_profile_plans_no_agent(project: Path, team_plugin_root: Path, answers) -> None:
    answers["profiles"] = [FLAT_PROFILE]
    plan = _plan(project, team_plugin_root, answers)
    assert _agent_steps(plan) == []
    assert setup.AGENTS_DIR not in setup.render_plan(plan)


@pytest.mark.parametrize("mode", ["setup", "update"])
def test_an_agent_follows_the_same_outcomes_as_the_rules(
    project: Path, team_plugin_root: Path, answers, setup_run, mode: str
) -> None:
    """By content and by the record, never by presence: unchanged while it is what the
    harness writes, an update when the harness's own rendering moved, a conflict when it
    was edited after the harness wrote it — exactly as `.harnex/rules.md`, in either mode."""
    answers["profiles"] = [TEAM_PROFILE]
    code, _ = setup_run("write", project, answers, plugin_root=team_plugin_root)
    assert code == 0
    first, second, third = team_agent_paths()

    def plan() -> setup.Plan:
        commit_all(project)
        return setup.build_plan(
            project,
            team_plugin_root,
            setup.read_answers(json.dumps(answers), team_plugin_root),
            mode=mode,
        )

    current = plan()
    assert all(_step(current, path).action == setup.UNCHANGED for path in (first, second, third))
    assert not current.conflicts

    specialist = first.removeprefix(f"{setup.AGENTS_DIR}{TEAM_PROFILE}-").removesuffix(".md")
    fragment = team_plugin_root / "tools" / "profiles" / TEAM_PROFILE / f"{specialist}.md"
    fragment.write_text("The fragment changed.\n", encoding="utf-8")
    moved = plan()
    assert _step(moved, first).action == setup.UPDATE
    assert _step(moved, first).data == render_agents.render([TEAM_PROFILE], team_plugin_root)[first]
    assert _step(moved, second).action == setup.UNCHANGED

    (project / second).write_text("edited by hand\n", encoding="utf-8")
    edited = plan()
    assert _step(edited, second).action == setup.CONFLICT
    assert any(second in c and "edited after the harness wrote it" in c for c in edited.conflicts)
    assert _step(edited, third).action == setup.UNCHANGED


def test_a_hand_written_agent_the_harness_never_recorded_says_so(
    project: Path, team_plugin_root: Path, answers, setup_run
) -> None:
    """The conflict sentence tells the two cases apart: a path the record lists was
    edited after the harness wrote it; a path it never lists — written by hand, or
    removed by the harness and written again since — is one the harness has no record
    of writing. Both are conflicts; only the second sentence is true of the second."""
    answers["profiles"] = []
    code, _ = setup_run("write", project, answers, plugin_root=team_plugin_root)
    assert code == 0
    first, _, _ = team_agent_paths()
    (project / first).parent.mkdir(parents=True, exist_ok=True)
    (project / first).write_text("---\nname: mine\ndescription: mine\n---\n\nMine.\n", encoding="utf-8")
    commit_all(project)

    answers["profiles"] = [TEAM_PROFILE]
    plan = _plan(project, team_plugin_root, answers)
    assert _step(plan, first).action == setup.CONFLICT
    conflict = next(c for c in plan.conflicts if first in c)
    assert "has no record of writing it" in conflict
    assert "edited after the harness wrote it" not in conflict


def test_a_fragment_the_renderer_refuses_stops_setup_as_its_own_refusal(
    project: Path, team_plugin_root: Path, answers, setup_run
) -> None:
    """A stray fragment is an ordinary `SetupError`: shown like any other refusal, no
    traceback, nothing planned and nothing written."""
    stray = team_plugin_root / "tools" / "profiles" / TEAM_PROFILE / "nobody.md"
    stray.write_text("For a role the harness does not hold.\n", encoding="utf-8")
    answers["profiles"] = [TEAM_PROFILE]
    with pytest.raises(setup.SetupError, match="nobody.md"):
        _plan(project, team_plugin_root, answers)
    code, said = setup_run("write", project, answers, plugin_root=team_plugin_root)
    assert code == 1
    assert said.startswith("setup: ") and "names no role" in said
    assert "Traceback" not in said
    assert not (project / ".claude" / "agents").exists()


# --- the clean-tree precondition and the rendered agents (design.md D3) ----------------


def test_a_shared_rerun_with_rendered_agents_uncommitted_plans_nothing_to_do(
    project: Path, team_plugin_root: Path, answers, setup_run
) -> None:
    answers["profiles"] = [TEAM_PROFILE]
    code, _ = setup_run("write", project, answers, plugin_root=team_plugin_root)
    assert code == 0
    status = git(project, "status", "--porcelain", "--untracked-files=all").stdout
    assert all(path in status for path in team_agent_paths()), "the agents are uncommitted"

    plan = _plan_as_is(project, team_plugin_root, answers)
    assert not plan.conflicts
    assert all(step.path != setup.GIT_DIR for step in plan.steps)
    assert plan.nothing_to_do
    code, said = setup_run("write", project, answers, commit=False, plugin_root=team_plugin_root)
    assert code == 0 and "Nothing to do" in said


@pytest.mark.parametrize("profiles", [[], [TEAM_PROFILE]])
def test_an_untracked_project_agent_is_a_conflict_like_any_other_path(
    project: Path, team_plugin_root: Path, answers, profiles: list[str]
) -> None:
    """`.claude/agents/` itself is never exempt: an agent the project wrote, with a team
    beside it or with no team at all, counts against the tree like any other path."""
    answers["profiles"] = profiles
    commit_all(project)
    own = project / ".claude" / "agents" / "own.md"
    own.parent.mkdir(parents=True)
    own.write_text("# Mine\n", encoding="utf-8")
    conflict = _refused(_plan_as_is(project, team_plugin_root, answers))
    assert [line.split()[-1] for line in conflict.splitlines()[1:]] == [".claude/agents/own.md"]


def test_a_recorded_agent_the_profiles_no_longer_render_does_not_count_against_the_tree(
    project: Path, team_plugin_root: Path, answers, setup_run
) -> None:
    """The profile is dropped before its agents were committed: the record still lists
    them, so they are the harness's own and the precondition holds for the run that is
    to remove them. (Only the precondition is checked here; their removal is planned by
    the next task.)"""
    answers["profiles"] = [TEAM_PROFILE]
    code, _ = setup_run("write", project, answers, plugin_root=team_plugin_root)
    assert code == 0
    record = json.loads((project / setup.MANIFEST).read_text(encoding="utf-8"))
    assert set(team_agent_paths()) <= set(record["paths"])

    answers["profiles"] = []
    plan = _plan_as_is(project, team_plugin_root, answers)
    assert all(step.path != setup.GIT_DIR for step in plan.steps)
    assert not plan.conflicts


# --- removal of an agent the profiles no longer render (design.md D3) ------------------


def _record_of(project: Path) -> dict:
    return json.loads((project / setup.MANIFEST).read_text(encoding="utf-8"))


@pytest.mark.parametrize("mode", ["setup", "update"])
def test_a_dropped_profile_plans_the_removal_of_its_agents(
    project: Path, team_plugin_root: Path, answers, setup_run, mode: str
) -> None:
    """Each agent the record lists and the choices no longer produce, still as the
    harness wrote it, is one `remove` line of the plan — the one deletion the harness
    ever plans, approved with the rest of the plan — and the record written last no
    longer lists it. In either mode: `update` reaches it through the same plan."""
    answers["profiles"] = [TEAM_PROFILE]
    code, _ = setup_run("write", project, answers, plugin_root=team_plugin_root)
    assert code == 0
    assert set(team_agent_paths()) <= set(_record_of(project)["paths"])

    answers["profiles"] = []
    commit_all(project)
    plan = setup.build_plan(
        project,
        team_plugin_root,
        setup.read_answers(json.dumps(answers), team_plugin_root),
        mode=mode,
    )
    assert not plan.conflicts
    assert [step.path for step in plan.removals] == team_agent_paths()
    for step in plan.removals:
        assert (step.owner, step.action, step.data) == ("harness", setup.REMOVE, None)
        assert "no longer rendered" in step.detail
    assert not plan.nothing_to_do, "a removal is work to do"
    record = _step(plan, setup.MANIFEST)
    assert record.action == setup.UPDATE and record.data is not None
    assert not any(path in record.data.decode("utf-8") for path in team_agent_paths())
    assert plan.steps[-1].path == setup.MANIFEST, "the record is still written last"
    said = setup.render_plan(plan)
    assert all(f"remove    {path}" in said for path in team_agent_paths())
    assert "3 to remove" in said


def test_an_edited_stale_agent_is_a_conflict_and_adoption_is_not_offered(
    project: Path, team_plugin_root: Path, answers, setup_run
) -> None:
    """Only an agent that is still what the harness wrote is the harness's to delete.
    One edited since is reported, named, and left where it is — the person deletes it by
    hand or restores it; the others, untouched, are still planned for removal."""
    answers["profiles"] = [TEAM_PROFILE]
    code, _ = setup_run("write", project, answers, plugin_root=team_plugin_root)
    assert code == 0
    first, *rest = team_agent_paths()
    (project / first).write_text("edited by hand\n", encoding="utf-8")

    answers["profiles"] = []
    plan = _plan(project, team_plugin_root, answers)
    assert _step(plan, first).action == setup.CONFLICT
    assert [step.path for step in plan.removals] == rest
    conflict = next(c for c in plan.conflicts if first in c)
    assert "edited after the harness wrote it" in conflict
    assert "adopt" not in conflict, "a removal is never adopted"
    assert "Delete it by hand" in conflict

    answers["approvals"]["adopt"] = [first]
    with pytest.raises(setup.SetupError, match="cannot adopt"):
        setup.read_answers(json.dumps(answers), team_plugin_root)


def test_a_stale_agent_already_deleted_by_hand_drops_silently_from_the_record(
    project: Path, team_plugin_root: Path, answers, setup_run
) -> None:
    answers["profiles"] = [TEAM_PROFILE]
    code, _ = setup_run("write", project, answers, plugin_root=team_plugin_root)
    assert code == 0
    first, *rest = team_agent_paths()
    (project / first).unlink()

    answers["profiles"] = []
    plan = _plan(project, team_plugin_root, answers)
    assert not plan.conflicts
    assert all(step.path != first for step in plan.steps), "nothing to say about it"
    assert [step.path for step in plan.removals] == rest
    assert first not in _step(plan, setup.MANIFEST).data.decode("utf-8")

    code, _ = setup_run("write", project, answers, plugin_root=team_plugin_root)
    assert code == 0
    assert not any(path in _record_of(project)["paths"] for path in team_agent_paths())


def test_an_agent_the_record_never_listed_is_never_removed(
    project: Path, team_plugin_root: Path, answers
) -> None:
    """Whatever sits under `.claude/agents/`, with no record of the harness having
    written it there is nothing for the harness to remove — even at a path a profile
    would render."""
    for name in ("own.md", f"{TEAM_PROFILE}-reviewer.md"):
        path = project / ".claude" / "agents" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Mine\n", encoding="utf-8")
    plan = _plan(project, team_plugin_root, answers)
    assert not plan.conflicts and not plan.removals
    assert not any(step.path.startswith(setup.AGENTS_DIR) for step in plan.steps)


def test_a_removal_alone_is_work_to_do(project: Path) -> None:
    plan = setup.Plan(project=project)
    assert plan.nothing_to_do
    removal = setup.Step(team_agent_paths()[0], "harness", setup.REMOVE, "no longer rendered")
    plan.steps.append(removal)
    assert not plan.writes and not plan.conflicts
    assert plan.removals == [removal]
    assert not plan.nothing_to_do


# --- what the offer says a profile brings (project-setup spec; design.md D1, D7) -------


def _offer_member(plugin_root: Path, specialist: str) -> dict[str, str]:
    """What the offer must say about one specialist, read from the role itself: its emoji
    is the role description's first code point (design.md D7), its phase the role's."""
    role = render_agents.read_role(render_agents.roles_dir(plugin_root) / f"{specialist}.md")
    return {"specialist": specialist, "emoji": role.description[0], "phase": role.phase}


def test_the_offer_says_which_specialists_each_profile_brings(team_plugin_root: Path) -> None:
    on_offer = setup.choices_on_offer(team_plugin_root)
    assert all(isinstance(name, str) for name in on_offer["profiles"]), "still a flat list"
    assert {TEAM_PROFILE, FLAT_PROFILE} <= set(on_offer["profiles"])
    teams = on_offer["teams"]
    assert set(teams) == set(on_offer["profiles"]), "every profile on offer has a team entry"
    assert teams[TEAM_PROFILE] == [
        _offer_member(team_plugin_root, specialist) for specialist in sorted(TEAM_SPECIALISTS)
    ], "the three specialists, sorted by name, each with its emoji and phase"
    assert teams[FLAT_PROFILE] == []
    for member in teams[TEAM_PROFILE]:
        assert len(member["emoji"]) == 1, "one code point, as the role's description opens"
        assert member["phase"] in render_agents.FRAGMENT_PHASES


def test_the_shipped_offer_maps_every_profile_to_its_team(plugin_root: Path) -> None:
    on_offer = setup.choices_on_offer(plugin_root)
    assert set(on_offer["teams"]) == set(on_offer["profiles"])
    profiles = plugin_root / "tools" / "profiles"
    for profile, team in on_offer["teams"].items():
        assert isinstance(team, list)
        if not (profiles / profile).is_dir():
            assert team == [], f"{profile} is a single-file profile and brings nobody"


def test_a_fragment_the_renderer_refuses_is_refused_by_the_offer_too(
    team_plugin_root: Path,
) -> None:
    """The offer must not list a team the plan would then refuse: a stray fragment is the
    same `SetupError` here as it is when planning."""
    stray = team_plugin_root / "tools" / "profiles" / TEAM_PROFILE / "nobody.md"
    stray.write_text("For a role the harness does not hold.\n", encoding="utf-8")
    with pytest.raises(setup.SetupError, match="nobody.md"):
        setup.choices_on_offer(team_plugin_root)


def test_the_choices_verb_prints_the_teams_with_the_rest(team_plugin_root: Path) -> None:
    out = io.StringIO()
    with redirect_stdout(out):
        code = setup.main(["choices", "--plugin-root", str(team_plugin_root)])
    assert code == 0
    printed = json.loads(out.getvalue())
    assert printed["teams"] == setup.choices_on_offer(team_plugin_root)["teams"]
    assert printed["teams"][TEAM_PROFILE][0]["specialist"] == sorted(TEAM_SPECIALISTS)[0]
