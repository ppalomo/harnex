"""What `update.run_update` and its CLI do: refuse, stop on conflict, or write.

Update never assembles an answers document by hand — it reads a project's own
`.harnex.yml` and plans from there (D2), then writes in the same pass, with no approval
gate, since everything in an update plan was already approved through setup's own yes
(design.md D3). These tests exercise the three ways that run can end: refusing before a
read, stopping before a write, and writing.
"""

import json
import shutil
from pathlib import Path

import pytest

import setup
import update
from conftest import tree


def test_refuses_when_the_project_was_never_set_up(project: Path, plugin_root: Path) -> None:
    with pytest.raises(setup.SetupError) as refusal:
        update.run_update(project, plugin_root)
    message = str(refusal.value)
    assert "setup" in message.lower()
    assert not list(project.iterdir()), "the refusal must write nothing"


def test_refuses_when_choices_are_recorded_but_the_manifest_is_absent(
    project: Path, answers, setup_run, plugin_root: Path
) -> None:
    setup_run("write", project, answers)
    (project / setup.MANIFEST).unlink()
    before = tree(project)

    with pytest.raises(setup.SetupError) as refusal:
        update.run_update(project, plugin_root)
    message = str(refusal.value)
    assert "setup" in message.lower()
    assert "adopt" in message.lower() or "guess" in message.lower()
    assert tree(project) == before, "the refusal must write nothing, including no manifest"


def test_a_conflict_stops_the_run_before_any_write(
    project: Path, answers, setup_run, plugin_root: Path
) -> None:
    setup_run("write", project, answers)
    (project / setup.RULES).write_text("hand-edited after setup wrote it\n", encoding="utf-8")
    before = tree(project)

    report, ok = update.run_update(project, plugin_root)
    assert ok is False
    assert "approve its adoption" in report
    assert tree(project) == before, "a conflict must stop the run before any write"


def test_a_clean_run_rewrites_rules_after_a_rule_changed_and_nothing_else_moves(
    project: Path, answers, setup_run, plugin_root: Path, tmp_path: Path
) -> None:
    setup_run("write", project, answers)
    before = tree(project)

    edited_root = tmp_path / "plugin-with-an-edited-rule"
    shutil.copytree(plugin_root, edited_root)
    rule_path = edited_root / "context" / "rules" / "git" / "conventional-commits.md"
    rule_path.write_text(
        rule_path.read_text(encoding="utf-8") + "\nAn added sentence.\n", encoding="utf-8"
    )

    report, ok = update.run_update(project, edited_root)
    assert ok is True
    assert "Written:" in report

    after = tree(project)
    assert set(after) == set(before), "no path appeared or disappeared"
    changed = {path for path in before if before[path] != after[path]}
    assert changed == {setup.RULES, setup.MANIFEST}, (
        "only the rendered rules and the record that hashes it should move"
    )
    assert "An added sentence." in after[setup.RULES].decode("utf-8")


def test_a_second_clean_run_changes_nothing(
    project: Path, answers, setup_run, plugin_root: Path
) -> None:
    setup_run("write", project, answers)
    before = tree(project)

    report, ok = update.run_update(project, plugin_root)
    assert ok is True
    assert "Nothing to do" in report
    assert tree(project) == before


def test_an_interrupted_update_recovers_by_content(
    project: Path, answers, setup_run, plugin_root: Path, tmp_path: Path
) -> None:
    """An interruption landing between a harness file's own write and the manifest's,
    written last, leaves the file already at the content this run would write, with the
    record still pointing at the old one. Update must recognise that by content -- the
    same way `setup.py`'s own interruption test (`test_setup_write.py`,
    `test_an_interruption_after_any_write_completes_on_the_next_run`) proves a first run
    does -- and finish by writing only what is left, reaching the same tree an
    uninterrupted run reaches."""
    setup_run("write", project, answers)

    edited_root = tmp_path / "plugin-with-an-edited-rule"
    shutil.copytree(plugin_root, edited_root)
    rule_path = edited_root / "context" / "rules" / "git" / "conventional-commits.md"
    rule_path.write_text(
        rule_path.read_text(encoding="utf-8") + "\nAn added sentence.\n", encoding="utf-8"
    )

    # What an uninterrupted run reaches, from the same starting point.
    reference_project = tmp_path / "reference"
    reference_project.mkdir()
    setup_run("write", reference_project, answers)
    _, reference_ok = update.run_update(reference_project, edited_root)
    assert reference_ok is True
    reference = tree(reference_project)

    # Simulate the interruption: write the rules file directly to the content this run
    # would produce -- the one write `write_atomic` would have completed -- without
    # touching the manifest, so the record is left stale, exactly as a stop right before
    # the manifest write would leave it.
    plan = setup.build_plan(
        project,
        edited_root,
        setup.read_answers(json.dumps(answers), edited_root),
        mode="update",
    )
    rules_step = next(step for step in plan.steps if step.path == setup.RULES)
    assert rules_step.data is not None, "the rule actually changed, or the test proves nothing"
    (project / setup.RULES).write_bytes(rules_step.data)
    assert (project / setup.MANIFEST).read_bytes() != reference[setup.MANIFEST], (
        "the record must still be the stale one for this to simulate an interruption"
    )

    report, ok = update.run_update(project, edited_root)
    assert ok is True
    assert "Written:" in report and setup.MANIFEST in report, (
        "recovery completes by writing what the interruption left behind"
    )
    assert tree(project) == reference, (
        "an interruption after the rules file and before the manifest did not recover "
        "to the same tree an uninterrupted run reaches"
    )


def test_a_fresh_clone_restores_state_ignore_unaided(
    project: Path, answers, setup_run, plugin_root: Path
) -> None:
    """A fresh clone carries every committed path but not `.harnex/state/`, which is
    gitignored and so never committed. Update must restore it from the project's own
    recorded choices, asking nothing, and report every other committed path unchanged."""
    setup_run("write", project, answers)

    state_dir = project / ".harnex" / "state"
    assert state_dir.is_dir(), "the project must have a state directory to simulate removing"
    shutil.rmtree(state_dir)
    before = tree(project)
    assert setup.STATE_IGNORE not in before, "the clone simulation must drop the state dir"

    report, ok = update.run_update(project, plugin_root)
    assert ok is True
    assert "Written:" in report and setup.STATE_IGNORE in report

    after = tree(project)
    assert (project / setup.STATE_IGNORE).is_file(), "the state directory must be restored"
    assert set(after) - set(before) == {setup.STATE_IGNORE}, (
        "only the state directory's own ignore file should reappear"
    )
    unchanged = {path for path in before if path in after}
    assert all(before[path] == after[path] for path in unchanged), (
        "every other committed path must be reported unchanged"
    )


def test_the_cli_exits_one_and_names_setup_when_never_set_up(
    project: Path, plugin_root: Path, capsys
) -> None:
    code = update.main(["--project", str(project), "--plugin-root", str(plugin_root)])
    assert code == 1
    out, err = capsys.readouterr()
    assert "setup" in (out + err).lower()


def test_the_cli_exits_zero_and_reports_what_it_wrote(
    project: Path, answers, setup_run, plugin_root: Path, tmp_path: Path, capsys
) -> None:
    setup_run("write", project, answers)

    edited_root = tmp_path / "plugin-with-an-edited-rule"
    shutil.copytree(plugin_root, edited_root)
    rule_path = edited_root / "context" / "rules" / "git" / "conventional-commits.md"
    rule_path.write_text(
        rule_path.read_text(encoding="utf-8") + "\nAn added sentence.\n", encoding="utf-8"
    )

    code = update.main(["--project", str(project), "--plugin-root", str(edited_root)])
    assert code == 0
    out, _ = capsys.readouterr()
    assert "Written:" in out
    assert setup.RULES in out
