"""`scope_check.py`: what `propose` uses to report a write outside its own change's
directory — the enforcer `the-proposal-is-the-scope` names.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import scope_check


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


def _snapshot(project: Path) -> str:
    return scope_check._status_text(project)


def test_a_clean_run_reports_nothing(repo: Path) -> None:
    before = _snapshot(repo)
    assert scope_check.scope_violations(repo, "my-change", before) == []


def test_a_write_inside_the_change_is_not_reported(repo: Path) -> None:
    before = _snapshot(repo)
    change_dir = repo / "openspec" / "changes" / "my-change"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text("why\n", encoding="utf-8")
    assert scope_check.scope_violations(repo, "my-change", before) == []


def test_a_write_outside_the_change_is_reported(repo: Path) -> None:
    before = _snapshot(repo)
    (repo / "somewhere-else.py").write_text("oops\n", encoding="utf-8")
    assert scope_check.scope_violations(repo, "my-change", before) == ["somewhere-else.py"]


def test_a_path_already_dirty_before_is_never_reported(repo: Path) -> None:
    (repo / "already-dirty.txt").write_text("pre-existing edit\n", encoding="utf-8")
    before = _snapshot(repo)
    assert "already-dirty.txt" in before  # sanity: the fixture really is dirty already

    change_dir = repo / "openspec" / "changes" / "my-change"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text("why\n", encoding="utf-8")
    (repo / "already-dirty.txt").write_text("edited again during propose\n", encoding="utf-8")

    assert scope_check.scope_violations(repo, "my-change", before) == []


def test_a_rename_outside_the_change_is_reported_by_its_new_path(repo: Path) -> None:
    before = _snapshot(repo)
    _git(repo, "mv", "README.md", "RENAMED.md")
    assert scope_check.scope_violations(repo, "my-change", before) == ["RENAMED.md"]


def test_main_reports_nothing_for_a_clean_run(repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    snapshot = tmp_path / "before.txt"
    snapshot.write_text(_snapshot(repo), encoding="utf-8")
    code = scope_check.main(["check", "--change", "my-change", "--before", str(snapshot), "--project", str(repo)])
    assert code == 0
    assert "Nothing was written outside" in capsys.readouterr().out


def test_main_reports_a_violation(repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    snapshot = tmp_path / "before.txt"
    snapshot.write_text(_snapshot(repo), encoding="utf-8")
    (repo / "stray.py").write_text("oops\n", encoding="utf-8")
    code = scope_check.main(["check", "--change", "my-change", "--before", str(snapshot), "--project", str(repo)])
    assert code == 0  # finding something is not a script failure
    out = capsys.readouterr().out
    assert "stray.py" in out


def test_main_fails_when_the_snapshot_cannot_be_read(repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    code = scope_check.main(
        ["check", "--change", "my-change", "--before", str(tmp_path / "missing.txt"), "--project", str(repo)]
    )
    assert code == 1
    assert "scope-check:" in capsys.readouterr().err


def test_main_fails_outside_a_git_repository(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    not_a_repo = tmp_path / "plain"
    not_a_repo.mkdir()
    snapshot = tmp_path / "before.txt"
    snapshot.write_text("", encoding="utf-8")
    code = scope_check.main(
        ["check", "--change", "my-change", "--before", str(snapshot), "--project", str(not_a_repo)]
    )
    assert code == 1
    assert "scope-check:" in capsys.readouterr().err
