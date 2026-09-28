"""`task_scope_check.py`: the path and protected-path checks the apply loop runs after a
builder writes — the detection `no-scope-beyond-the-task` and `builders-never-tick-tasks`
now name.
"""

from __future__ import annotations

import task_scope_check as check


def _porcelain(*paths: str) -> str:
    return "\n".join(f"?? {path}" for path in paths)


def test_a_write_inside_a_declared_path_is_not_a_violation() -> None:
    before = _porcelain()
    after = _porcelain("plugin/feedback/task_scope_check.py")
    assert check.check_declared(["plugin/feedback/task_scope_check.py"], before, after) == []


def test_a_write_inside_a_declared_directory_is_not_a_violation() -> None:
    before = _porcelain()
    after = _porcelain("plugin/feedback/new_module.py")
    assert check.check_declared(["plugin/feedback"], before, after) == []


def test_a_write_outside_declared_paths_is_a_violation() -> None:
    before = _porcelain()
    after = _porcelain("plugin/scripts/decide.py")
    assert check.check_declared(["plugin/feedback"], before, after) == ["plugin/scripts/decide.py"]


def test_a_path_already_dirty_before_is_not_reported() -> None:
    before = _porcelain("already-dirty.txt")
    after = _porcelain("already-dirty.txt", "plugin/scripts/decide.py")
    assert check.check_declared(["plugin/feedback"], before, after) == ["plugin/scripts/decide.py"]


def test_openspec_is_always_protected() -> None:
    before = _porcelain()
    after = _porcelain("openspec/changes/x/tasks.md")
    assert check.check_protected(before, after) == ["openspec/changes/x/tasks.md"]


def test_harnex_state_is_always_protected() -> None:
    before = _porcelain()
    after = _porcelain(".harnex/state/apply/x.json")
    assert check.check_protected(before, after) == [".harnex/state/apply/x.json"]


def test_a_declared_path_cannot_widen_past_a_protected_path() -> None:
    """A task that names `openspec/changes/x/tasks.md` as one of its own declared paths
    is still refused — declared scope never overrides the protected list."""
    before = _porcelain()
    after = _porcelain("openspec/changes/x/tasks.md")
    declared = check.check_declared(["openspec/changes/x/tasks.md"], before, after)
    assert declared == [], "the path check alone has no opinion on protection"
    assert check.check_protected(before, after) == ["openspec/changes/x/tasks.md"]


def test_an_unprotected_write_outside_openspec_and_harnex_is_not_flagged() -> None:
    before = _porcelain()
    after = _porcelain("plugin/scripts/decide.py")
    assert check.check_protected(before, after) == []


def test_a_rename_is_reported_by_its_new_path() -> None:
    before = _porcelain()
    after = "R  old/path.py -> plugin/feedback/new.py"
    assert check.check_declared(["plugin/feedback"], before, after) == []
