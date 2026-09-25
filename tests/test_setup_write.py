"""What setting a project up actually writes, and what it refuses to touch.

The snapshots pin the exact bytes a choice produces, so a change to a template, to the
floor or to a rule shows up here as a diff to read rather than as a surprise in someone's
project. Regenerate them with:

    HARNEX_UPDATE_SNAPSHOTS=1 uv run --with pytest pytest tests/test_setup_write.py

and read the diff before committing it.
"""

import json
import os
import shutil
from pathlib import Path

import pytest

import setup
from conftest import tree

SNAPSHOTS = Path(__file__).resolve().parent / "snapshots"
DELIMITER = "===== "


def _as_text(project: Path) -> str:
    parts = []
    for path, body in tree(project).items():
        parts.append(f"{DELIMITER}{path}\n{body.decode('utf-8')}")
    return "".join(parts)


def _check_snapshot(project: Path, name: str) -> None:
    snapshot = SNAPSHOTS / name
    rendered = _as_text(project)
    if os.environ.get("HARNEX_UPDATE_SNAPSHOTS"):
        snapshot.write_text(rendered, encoding="utf-8")
    assert rendered == snapshot.read_text(encoding="utf-8"), (
        f"{name} has moved. Read the diff, then regenerate it with the command in this "
        "module's docstring."
    )


def test_a_project_with_every_set(project: Path, answers, setup_run) -> None:
    code, _ = setup_run("write", project, answers)
    assert code == 0
    _check_snapshot(project, "setup-all-sets.md")


def test_a_project_with_one_set(project: Path, answers, setup_run) -> None:
    answers["sets"] = ["git"]
    answers["canary"] = ""
    code, _ = setup_run("write", project, answers)
    assert code == 0
    _check_snapshot(project, "setup-one-set.md")


def test_a_second_run_changes_nothing(project: Path, answers, setup_run) -> None:
    setup_run("write", project, answers)
    before = tree(project)
    code, said = setup_run("write", project, answers)
    assert code == 0
    assert tree(project) == before, "a second run moved a byte, including the record"
    assert "Nothing to do" in said


def test_a_fresh_clone_restores_only_what_is_not_committed(
    project: Path, answers, setup_run, tmp_path: Path
) -> None:
    """The record is committed, so a clone is recognised. The runtime state is not, so
    the one path a clone is missing is the one the project deliberately does not keep."""
    setup_run("write", project, answers)
    clone = tmp_path / "clone"
    clone.mkdir()
    for path, body in tree(project).items():
        if path.startswith(".harnex/state/"):
            continue
        (clone / path).parent.mkdir(parents=True, exist_ok=True)
        (clone / path).write_bytes(body)

    code, said = setup_run("plan", clone, answers)
    assert code == 0
    writes = [line for line in said.splitlines() if " create " in line or " update " in line]
    assert len(writes) == 1 and setup.STATE_IGNORE in writes[0]


def test_an_interruption_after_any_write_completes_on_the_next_run(
    project: Path, answers, setup_run, monkeypatch, tmp_path: Path
) -> None:
    reference_project = tmp_path / "reference"
    reference_project.mkdir()
    setup_run("write", reference_project, answers)
    reference = {
        path: body for path, body in tree(reference_project).items()
    }

    total = len(reference)
    for stop_after in range(total):  # before the first write, and after each of them
        shutil.rmtree(project)
        project.mkdir()

        written = {"count": 0}
        real = setup.write_atomic

        def fail_after(path: Path, data: bytes) -> None:
            if written["count"] >= stop_after:
                raise KeyboardInterrupt(f"interrupted before write {stop_after + 1}")
            written["count"] += 1
            real(path, data)

        monkeypatch.setattr(setup, "write_atomic", fail_after)
        with pytest.raises(KeyboardInterrupt):
            setup_run("write", project, answers)
        monkeypatch.setattr(setup, "write_atomic", real)

        leftovers = [p.name for p in project.rglob("*.tmp")]
        assert not leftovers, f"an interrupted write left {leftovers}"

        code, _ = setup_run("write", project, answers)
        assert code == 0
        assert tree(project) == reference, (
            f"interrupting after {stop_after} write(s) did not resume to the same tree"
        )


def test_the_project_s_own_files_are_never_rewritten(project: Path, answers, setup_run) -> None:
    own = {
        "AGENTS.md": "# Mine\n\nIt does a thing, and it points at `.harnex/rules.md`.\n",
        "CLAUDE.md": "@AGENTS.md\n@.harnex/rules.md\n\n# Mine\n",
        "openspec/config.yaml": "schema: spec-driven\n",
    }
    for path, body in own.items():
        (project / path).parent.mkdir(parents=True, exist_ok=True)
        (project / path).write_text(body, encoding="utf-8")

    code, _ = setup_run("write", project, answers)
    assert code == 0
    for path, body in own.items():
        assert (project / path).read_text(encoding="utf-8") == body


def test_a_pointer_line_is_inserted_only_when_it_was_approved(
    project: Path, answers, setup_run
) -> None:
    (project / "AGENTS.md").write_text("# Mine\n\nIt does a thing.\n", encoding="utf-8")
    (project / "CLAUDE.md").write_text("# Mine\n", encoding="utf-8")

    code, said = setup_run("write", project, answers)
    assert code == 0
    assert (project / "AGENTS.md").read_text(encoding="utf-8") == "# Mine\n\nIt does a thing.\n"
    assert "does not point at" in said, "the notice says what does not work"

    _, said_again = setup_run("plan", project, answers)
    assert "does not point at" in said_again, "and it is repeated on every later run"

    answers["approvals"]["pointer_agents"] = True
    answers["approvals"]["pointer_claude"] = True
    setup_run("write", project, answers)
    agents = (project / "AGENTS.md").read_text(encoding="utf-8")
    claude = (project / "CLAUDE.md").read_text(encoding="utf-8")
    assert agents.startswith("# Mine\n\nIt does a thing.\n")
    assert ".harnex/rules.md" in agents
    assert claude.startswith("@AGENTS.md\n@.harnex/rules.md\n")

    setup_run("write", project, answers)
    assert (project / "AGENTS.md").read_text(encoding="utf-8") == agents, "insertion repeats"
    assert (project / "CLAUDE.md").read_text(encoding="utf-8") == claude


def test_adoption_replaces_only_after_the_difference_was_shown(
    project: Path, answers, setup_run
) -> None:
    (project / ".harnex").mkdir()
    foreign = "rules I wrote by hand\n"
    (project / setup.RULES).write_text(foreign, encoding="utf-8")

    code, said = setup_run("write", project, answers)
    assert code == 1 and "approve its adoption" in said
    assert (project / setup.RULES).read_text(encoding="utf-8") == foreign

    answers["approvals"]["adopt"] = [setup.RULES]
    code, _ = setup_run("write", project, answers)
    assert code == 0
    assert (project / setup.RULES).read_text(encoding="utf-8") != foreign


def test_the_runtime_state_ignores_itself_without_touching_the_project_s_rules(
    project: Path, answers, setup_run
) -> None:
    setup_run("write", project, answers)
    assert (project / setup.STATE_IGNORE).read_text(encoding="utf-8").strip().endswith("*")
    assert not (project / ".gitignore").exists(), "the project's own ignore file is untouched"

    (project / ".gitignore").write_text("build/\n", encoding="utf-8")
    setup_run("write", project, answers)
    assert (project / ".gitignore").read_text(encoding="utf-8") == "build/\n"


def test_the_record_holds_a_hash_for_every_path_the_harness_owns(
    project: Path, answers, setup_run
) -> None:
    setup_run("write", project, answers)
    record = json.loads((project / setup.MANIFEST).read_text(encoding="utf-8"))
    assert record["format"] == setup.MANIFEST_FORMAT
    assert set(record["paths"]) == set(setup.HARNESS_PATHS)
    for path, recorded in record["paths"].items():
        assert setup.digest((project / path).read_bytes()) == recorded
    assert "verified" not in json.dumps(record), "no stamp of any kind belongs in the record"


def test_the_record_is_written_last(project: Path, plugin_root: Path, answers) -> None:
    plan = setup.build_plan(
        project, plugin_root, setup.read_answers(json.dumps(answers), plugin_root)
    )
    assert plan.steps[-1].path == setup.MANIFEST


@pytest.mark.skipif(not shutil.which("uv"), reason="uv is how the host runs the script")
def test_the_script_runs_as_its_own_process(
    project: Path, answers, tmp_path: Path, plugin_root: Path
) -> None:
    """The host starts this as a process with a plain interpreter, not as an import."""
    import subprocess

    document = tmp_path / "answers.json"
    document.write_text(json.dumps(answers), encoding="utf-8")
    finished = subprocess.run(
        [
            "uv",
            "run",
            str(plugin_root / "scripts" / "setup.py"),
            "write",
            "--answers",
            str(document),
            "--project",
            str(project),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert finished.returncode == 0, finished.stderr
    assert (project / setup.MANIFEST).is_file()
    assert "Written:" in finished.stdout


def test_the_rules_file_is_the_renderer_s_own_output(
    project: Path, plugin_root: Path, answers, setup_run
) -> None:
    """Setup calls the renderer rather than reimplementing any part of it."""
    import render_rules

    setup_run("write", project, answers)
    expected = render_rules.render(
        answers["sets"], answers["profiles"], plugin_root / "context" / "rules"
    )
    assert (project / setup.RULES).read_text(encoding="utf-8") == expected


def test_the_record_does_not_depend_on_where_the_project_is(
    tmp_path: Path, answers, setup_run
) -> None:
    records = []
    for name in ("here", "somewhere/else/entirely"):
        elsewhere = tmp_path / name
        elsewhere.mkdir(parents=True)
        setup_run("write", elsewhere, answers)
        records.append((elsewhere / setup.MANIFEST).read_bytes())
    assert records[0] == records[1], "the record depends on the path it was written at"


def test_the_only_writes_to_a_project_owned_path_are_creation_and_the_approved_line(
    project: Path, plugin_root: Path, answers
) -> None:
    """Prevention, not intention: there is no other branch that writes one of these."""
    (project / "AGENTS.md").write_text("# Mine\n", encoding="utf-8")
    (project / "CLAUDE.md").write_text("# Mine\n", encoding="utf-8")
    answers["approvals"]["pointer_agents"] = True

    plan = setup.build_plan(
        project, plugin_root, setup.read_answers(json.dumps(answers), plugin_root)
    )
    for step in plan.steps:
        if step.owner == "project" and step.data is not None:
            assert step.action in (setup.CREATE, setup.INSERT)
            if step.action == setup.INSERT:
                assert step.path == "AGENTS.md", "only the approved file is written"
