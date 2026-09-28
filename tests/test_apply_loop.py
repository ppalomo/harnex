"""`apply_loop.py`: task parsing, ticking, fingerprinting, `task.route` batching,
`task.scope`, acceptance, and the run-state file — `apply`'s own deterministic steps.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import apply_loop
import decide


def _git(project: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(project), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    _git(project, "init", "-q")
    _git(project, "config", "user.email", "test@test.com")
    _git(project, "config", "user.name", "test")
    (project / "README.md").write_text("hello\n", encoding="utf-8")
    _git(project, "add", "-A")
    _git(project, "commit", "-q", "-m", "init")
    return project


# --- parsing tasks.md --------------------------------------------------------------------

TASKS_MD = """\
## 1. Setup

- [ ] 1.1 Write `plugin/feedback/task_scope_check.py` with tests
- [x] 1.2 Already done, no paths named
- [ ] 1.10 Not the same task as 1.1
"""


def test_parse_tasks_reads_id_text_and_done() -> None:
    tasks = apply_loop.parse_tasks(TASKS_MD)
    assert [t.id for t in tasks] == ["1.1", "1.2", "1.10"]
    assert tasks[0].done is False
    assert tasks[1].done is True


def test_declared_paths_come_from_backtick_spans_with_a_slash() -> None:
    tasks = apply_loop.parse_tasks(TASKS_MD)
    assert tasks[0].paths == ("plugin/feedback/task_scope_check.py",)
    assert tasks[1].paths == ()


def test_a_url_in_backticks_is_not_treated_as_a_path() -> None:
    paths = apply_loop.extract_declared_paths("See `https://openrouter.ai/api/alpha/decisions`")
    assert paths == ()


# --- ticking -------------------------------------------------------------------------------


def test_tick_task_marks_exactly_the_named_task(repo: Path) -> None:
    change_dir = repo / "openspec" / "changes" / "my-change"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(TASKS_MD, encoding="utf-8")

    apply_loop.tick_task(repo, "my-change", "1.1")

    text = (change_dir / "tasks.md").read_text(encoding="utf-8")
    assert "- [x] 1.1 Write" in text
    assert "- [ ] 1.10 Not the same task as 1.1" in text, "1.1 must not also tick 1.10"


def test_tick_task_refuses_a_task_already_ticked_or_missing(repo: Path) -> None:
    change_dir = repo / "openspec" / "changes" / "my-change"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(TASKS_MD, encoding="utf-8")

    with pytest.raises(apply_loop.ApplyLoopError):
        apply_loop.tick_task(repo, "my-change", "1.2")  # already [x]
    with pytest.raises(apply_loop.ApplyLoopError):
        apply_loop.tick_task(repo, "my-change", "9.9")  # does not exist


# --- fingerprinting --------------------------------------------------------------------


def test_identical_trees_fingerprint_identically(repo: Path) -> None:
    a = apply_loop.tree_fingerprint(repo, "HEAD")
    b = apply_loop.tree_fingerprint(repo, "HEAD")
    assert a == b


def test_a_single_byte_change_fingerprints_differently(repo: Path) -> None:
    before = apply_loop.tree_fingerprint(repo, "HEAD")
    (repo / "README.md").write_text("hello!\n", encoding="utf-8")
    after = apply_loop.tree_fingerprint(repo, "HEAD")
    assert before != after


def test_an_untracked_file_changes_the_fingerprint(repo: Path) -> None:
    before = apply_loop.tree_fingerprint(repo, "HEAD")
    (repo / "new_file.py").write_text("x = 1\n", encoding="utf-8")
    after = apply_loop.tree_fingerprint(repo, "HEAD")
    assert before != after


def test_reverting_a_change_restores_the_fingerprint(repo: Path) -> None:
    before = apply_loop.tree_fingerprint(repo, "HEAD")
    (repo / "README.md").write_text("hello!\n", encoding="utf-8")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    after = apply_loop.tree_fingerprint(repo, "HEAD")
    assert before == after


# --- routing: task.route batched across every task --------------------------------------


def _task(task_id: str, text: str, paths: tuple[str, ...] = ()) -> apply_loop.Task:
    return apply_loop.Task(id=task_id, text=text, done=False, paths=paths)


def test_route_all_with_mock_prints_one_line_per_task(repo: Path) -> None:
    tasks = [_task("1.1", "Write the check"), _task("1.2", "Write the loop")]
    results = apply_loop.route_all(repo, decide.default_decisions_dir(), tasks, "mock", None)
    assert [r["task_id"] for r in results] == ["1.1", "1.2"]
    assert all(not r["outcome"]["resolved"] for r in results)
    assert "1.1" in results[0]["line"]
    assert "1.2" in results[1]["line"]


def test_route_all_with_jev_sends_one_request_for_every_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks = [_task("1.1", "Write the check"), _task("1.2", "Write the loop")]
    calls = []

    def _post(body: dict, _key: str, timeout: float) -> dict:
        calls.append(body)
        return {
            "answers": {
                qid: {"type": "choice", "choice": "claude", "confidence": 0.9, "probabilities": {"claude": 0.9}}
                for qid in body["questions"]
            },
            "usage": {"cost": 0.00001},
        }

    monkeypatch.setattr(decide, "_post", _post)
    results = apply_loop.route_all(repo, decide.default_decisions_dir(), tasks, "jev", "k")
    assert len(calls) == 1, "one request answered every task's routing"
    assert set(calls[0]["questions"]) == {"task.route#0", "task.route#1"}
    assert calls[0]["state"] == {}, "no shared state — each question is self-contained"
    assert all(r["outcome"]["decision"] == "claude" for r in results)


def test_route_all_journals_one_line_per_task(repo: Path) -> None:
    tasks = [_task("1.1", "Write the check")]
    apply_loop.route_all(repo, decide.default_decisions_dir(), tasks, "mock", None)
    journal = decide.journal_path(repo)
    lines = journal.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["question"] == "task.route#0"


# --- task.scope: one call, after the builder has written --------------------------------


def test_ask_scope_with_mock_never_resolves(repo: Path) -> None:
    task = _task("2.1", "A task with no declared paths")
    outcome = apply_loop.ask_scope(repo, decide.default_decisions_dir(), task, "some/changed/path.py", "mock", None)
    assert outcome["resolved"] is False
    assert outcome["backend"] == "mock"


# --- acceptance: a conjunction, never a judgement ----------------------------------------


def _ok_acceptance(**overrides: object) -> apply_loop.Acceptance:
    fields = dict(
        builder_reported_done=True,
        check_exit_code=0,
        declared_violations=[],
        protected_violations=[],
        scope_outcome=None,
        head_moved=False,
        fingerprint_at_check="abc",
        fingerprint_at_acceptance="abc",
    )
    fields.update(overrides)
    return apply_loop.evaluate_acceptance(**fields)


def test_every_condition_holding_accepts() -> None:
    assert _ok_acceptance().accepted is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"builder_reported_done": False},
        {"check_exit_code": 1},
        {"declared_violations": ["plugin/scripts/decide.py"]},
        {"protected_violations": ["openspec/changes/x/tasks.md"]},
        {"head_moved": True},
        {"fingerprint_at_acceptance": "different"},
    ],
)
def test_any_single_condition_failing_refuses_acceptance(overrides: dict[str, object]) -> None:
    result = _ok_acceptance(**overrides)
    assert result.accepted is False
    assert result.reasons


def test_an_unresolved_scope_outcome_refuses_acceptance() -> None:
    result = _ok_acceptance(scope_outcome={"resolved": False})
    assert result.accepted is False


def test_a_resolved_out_of_scope_outcome_refuses_acceptance() -> None:
    result = _ok_acceptance(scope_outcome={"resolved": True, "decision": "false"})
    assert result.accepted is False


def test_a_resolved_in_scope_outcome_does_not_block_acceptance() -> None:
    result = _ok_acceptance(scope_outcome={"resolved": True, "decision": "true"})
    assert result.accepted is True


# --- run state: atomic, one entry per task ------------------------------------------------


def test_a_missing_state_file_loads_as_empty(tmp_path: Path) -> None:
    state = apply_loop.load_run_state(tmp_path, "my-change")
    assert state == {"change": "my-change", "tasks": {}}


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    state = {"change": "my-change", "tasks": {"1.1": {"status": "queued"}}}
    apply_loop.save_run_state(tmp_path, "my-change", state)
    assert apply_loop.load_run_state(tmp_path, "my-change") == state


def test_a_transition_updates_only_the_named_task(tmp_path: Path) -> None:
    state = {"change": "my-change", "tasks": {"1.1": {"status": "queued"}, "1.2": {"status": "queued"}}}
    apply_loop.transition(state, "1.1", "delegated", binding="codex")
    assert state["tasks"]["1.1"] == {"status": "delegated", "binding": "codex"}
    assert state["tasks"]["1.2"] == {"status": "queued"}


def test_an_unknown_transition_is_refused(tmp_path: Path) -> None:
    state = {"change": "my-change", "tasks": {}}
    with pytest.raises(apply_loop.ApplyLoopError):
        apply_loop.transition(state, "1.1", "vibes")


def test_save_run_state_is_atomic_no_half_written_file_survives(tmp_path: Path) -> None:
    state = {"change": "my-change", "tasks": {"1.1": {"status": "queued"}}}
    apply_loop.save_run_state(tmp_path, "my-change", state)
    path = apply_loop.run_state_path(tmp_path, "my-change")
    tmp_marker = path.with_suffix(".json.tmp")
    assert not tmp_marker.exists(), "the temp file must be renamed away, never left behind"

    apply_loop.transition(state, "1.1", "checked")
    apply_loop.save_run_state(tmp_path, "my-change", state)
    assert apply_loop.load_run_state(tmp_path, "my-change")["tasks"]["1.1"]["status"] == "checked"


def test_a_ticked_tasks_entry_is_never_revisited_by_the_caller() -> None:
    """The loop itself decides not to revisit an `accepted` task; this only documents
    that the state shape makes that check possible (the loop's own resume procedure is
    exercised in tasks 4.5/5.2's manual and skill-level tests, not here)."""
    state = {"change": "my-change", "tasks": {"1.1": {"status": "accepted"}, "1.2": {"status": "delegated"}}}
    in_flight = [tid for tid, entry in state["tasks"].items() if entry["status"] != "accepted"]
    assert in_flight == ["1.2"]


# --- resume classification: the recovery contract's own decision table ------------------


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        (None, "start-fresh"),
        ({"status": "queued"}, "start-fresh"),
        ({"status": "delegated", "binding": "codex", "job_id": "j1"}, "lookup-job"),
        ({"status": "returned"}, "resume-check"),
        ({"status": "checked"}, "resume-check"),
        ({"status": "accepted"}, "skip"),
    ],
)
def test_resume_action_classifies_every_recorded_status(entry: dict[str, object] | None, expected: str) -> None:
    assert apply_loop.resume_action(entry) == expected


def test_resuming_a_run_never_touches_an_accepted_task() -> None:
    state = {"change": "x", "tasks": {"1.1": {"status": "accepted"}, "1.2": {"status": "delegated"}}}
    actions = {tid: apply_loop.resume_action(entry) for tid, entry in state["tasks"].items()}
    assert actions["1.1"] == "skip"
    assert actions["1.2"] == "lookup-job"
