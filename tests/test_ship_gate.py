"""Tests for the stable verifier-review gate used by ``/harnex:ship``."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import ship_gate
from working_tree import tree_fingerprint


def _git(project: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(project), *args], check=True, capture_output=True)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    path = tmp_path / "project"
    path.mkdir()
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "test")
    _git(path, "config", "commit.gpgSign", "false")
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    state = path / ".harnex" / "state"
    state.mkdir(parents=True)
    (state / ".gitignore").write_text("*\n", encoding="utf-8")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "initial fixture")
    return path


def _write_review(
    project: Path, change: str, findings: list[dict[str, object]]
) -> None:
    fingerprint = tree_fingerprint(project, "HEAD")
    path = ship_gate.review_record_path(project, change)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "change": change,
                "base_ref": "HEAD",
                "fingerprint": fingerprint,
                "findings": findings,
            }
        ),
        encoding="utf-8",
    )


def test_no_verify_run_refuses_and_tells_the_person_to_verify(project: Path) -> None:
    result = ship_gate.check(project, "example-change")

    assert result == {
        "decision": "refuse",
        "reason": "no run found",
        "findings": [],
    }


def test_changed_tree_refuses_a_stale_review(project: Path) -> None:
    _write_review(project, "example-change", [])
    (project / "README.md").write_text("changed\n", encoding="utf-8")

    result = ship_gate.check(project, "example-change")

    assert result["decision"] == "refuse"
    assert result["reason"] == "stale fingerprint"


def test_fresh_clean_review_proceeds_and_returns_advisory_findings(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    findings = [{"severity": "advisory", "summary": "consider a small cleanup"}]
    _write_review(project, "example-change", findings)

    assert ship_gate.main(["check", "--project", str(project), "--change", "example-change"]) == 0
    result = json.loads(capsys.readouterr().out)

    assert result == {"decision": "go", "reason": None, "findings": findings}


def test_blocking_finding_refuses_a_fresh_review(project: Path) -> None:
    findings = [{"severity": "blocking", "summary": "the required check failed"}]
    _write_review(project, "example-change", findings)

    result = ship_gate.check(project, "example-change")

    assert result == {
        "decision": "refuse",
        "reason": "a blocking finding",
        "findings": findings,
    }


def test_record_round_trips_a_fresh_review_to_check(project: Path) -> None:
    findings = [{"severity": "advisory", "summary": "keep the public interface small"}]

    path = ship_gate.record(
        project,
        "example-change",
        base_ref="HEAD",
        fingerprint=tree_fingerprint(project, "HEAD"),
        findings=findings,
    )

    assert path == ship_gate.review_record_path(project, "example-change")
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "change": "example-change",
        "base_ref": "HEAD",
        "fingerprint": tree_fingerprint(project, "HEAD"),
        "findings": findings,
    }
    assert ship_gate.check(project, "example-change") == {
        "decision": "go",
        "reason": None,
        "findings": findings,
    }


@pytest.mark.parametrize(
    "record",
    [
        {"base_ref": "HEAD", "fingerprint": "fingerprint"},
        {"base_ref": "not-a-git-ref", "fingerprint": "fingerprint", "findings": []},
        {
            "base_ref": "HEAD",
            "fingerprint": "fingerprint",
            "findings": [{"severity": "critical"}],
        },
    ],
    ids=["missing-findings", "unknown-base-ref", "invalid-severity"],
)
def test_unreadable_review_records_refuse_safely(project: Path, record: dict[str, object]) -> None:
    path = ship_gate.review_record_path(project, "example-change")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")

    assert ship_gate.check(project, "example-change") == {
        "decision": "refuse",
        "reason": "an unreadable review record",
        "findings": [],
    }
