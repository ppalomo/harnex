"""The survey and the plan: what is there, what would happen to it, and what stops it.

Every class in the survey comes from the record and the bytes on disk, never from a
path's mere presence. That is what makes recovery possible without a journal: a file
that is already what the harness would write is recognised as current, whatever the
record says about it.
"""

import json
from pathlib import Path

import pytest

import setup
from conftest import tree


def _plan(project: Path, plugin_root: Path, answers: dict) -> setup.Plan:
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
