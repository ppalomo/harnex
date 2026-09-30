"""`verify_checks.py` records each configured check as facts for its input tree."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import verify_checks
from working_tree import tree_fingerprint


CHOICES = """\
project_name: fixture
profiles:
sets:
features:
canary: word
decision_model: mock
check_command: {check_command}
"""

CHOICES_WITHOUT_CHECK_COMMAND = """\
project_name: fixture
profiles:
sets:
features:
canary: word
decision_model: mock
"""


def _git(project: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(project), *args], check=True, capture_output=True)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    path = tmp_path / "project"
    path.mkdir()
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "test")
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    state = path / ".harnex" / "state"
    state.mkdir(parents=True)
    (state / ".gitignore").write_text("*\n", encoding="utf-8")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "initial fixture")
    return path


@pytest.mark.parametrize(
    ("command", "expected_status", "expected_output"),
    [
        ("printf 'passing check\\n'", 0, "passing check\n"),
        ("printf 'failing check\\n'; exit 1", 1, "failing check\n"),
    ],
)
def test_check_facts_capture_the_result_and_input_tree(
    project: Path, command: str, expected_status: int, expected_output: str
) -> None:
    (project / ".harnex.yml").write_text(
        CHOICES.format(check_command=command), encoding="utf-8"
    )
    _git(project, "add", ".harnex.yml")
    _git(project, "commit", "-q", "-m", "configure check")
    expected_fingerprint = tree_fingerprint(project, "HEAD")

    assert verify_checks.main(["--project", str(project)]) == expected_status

    facts_files = list((project / ".harnex" / "state" / "verify").glob("*.json"))
    assert len(facts_files) == 1
    facts = json.loads(facts_files[0].read_text(encoding="utf-8"))
    assert facts["exit_status"] == expected_status
    assert facts["output"] == expected_output
    assert facts["fingerprint"] == expected_fingerprint


def test_check_facts_fingerprint_includes_files_the_check_creates(project: Path) -> None:
    (project / ".harnex.yml").write_text(
        CHOICES.format(check_command="printf generated > check-artifact.txt"), encoding="utf-8"
    )
    _git(project, "add", ".harnex.yml")
    _git(project, "commit", "-q", "-m", "configure check")

    assert verify_checks.main(["--project", str(project)]) == 0

    facts_file = next((project / ".harnex" / "state" / "verify").glob("*.json"))
    facts = json.loads(facts_file.read_text(encoding="utf-8"))
    assert facts["fingerprint"] == tree_fingerprint(project, "HEAD")


def test_missing_check_command_reports_an_internal_error_without_writing_facts(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (project / ".harnex.yml").write_text(CHOICES_WITHOUT_CHECK_COMMAND, encoding="utf-8")

    assert verify_checks.main(["--project", str(project)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith(verify_checks.INTERNAL_ERROR_SENTINEL)
    assert not list((project / ".harnex" / "state" / "verify").glob("*.json"))


def test_ui_profile_records_stubbed_playwright_findings(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project / ".harnex.yml").write_text(
        CHOICES.replace("profiles:\n", "profiles:\n  - react\n").format(
            check_command="printf 'passing check\\n'"
        ),
        encoding="utf-8",
    )
    expected = {"status": "passed", "findings": [{"name": "homepage"}]}
    calls: list[Path] = []

    def stub_playwright_checks(received_project: Path) -> dict[str, object]:
        calls.append(received_project)
        return expected

    monkeypatch.setattr(verify_checks, "run_playwright_checks", stub_playwright_checks)

    assert verify_checks.main(["--project", str(project)]) == 0

    facts_file = next((project / ".harnex" / "state" / "verify").glob("*.json"))
    facts = json.loads(facts_file.read_text(encoding="utf-8"))
    assert calls == [project]
    assert facts["playwright"] == expected


def test_non_ui_profile_skips_playwright_checks(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project / ".harnex.yml").write_text(
        CHOICES.replace("profiles:\n", "profiles:\n  - fastapi\n").format(
            check_command="printf 'passing check\\n'"
        ),
        encoding="utf-8",
    )

    def unexpected_playwright_checks(_: Path) -> dict[str, object]:
        raise AssertionError("Playwright checks must not run without a UI profile")

    monkeypatch.setattr(verify_checks, "run_playwright_checks", unexpected_playwright_checks)

    assert verify_checks.main(["--project", str(project)]) == 0

    facts_file = next((project / ".harnex" / "state" / "verify").glob("*.json"))
    facts = json.loads(facts_file.read_text(encoding="utf-8"))
    assert facts["playwright"] == {
        "status": "skipped",
        "reason": "no UI profile declared",
    }


def test_a_profile_not_listed_in_ui_registry_skips_playwright_checks(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project / ".harnex.yml").write_text(
        CHOICES.replace("profiles:\n", "profiles:\n  - svelte\n").format(
            check_command="printf 'passing check\\n'"
        ),
        encoding="utf-8",
    )
    plugin_root = tmp_path / "plugin"
    registry = plugin_root / "tools" / "profiles" / "ui.json"
    registry.parent.mkdir(parents=True)
    registry.write_text('["react"]\n', encoding="utf-8")

    def unexpected_playwright_checks(_: Path) -> dict[str, object]:
        raise AssertionError("Playwright checks must not run without a declared UI profile")

    monkeypatch.setattr(verify_checks, "run_playwright_checks", unexpected_playwright_checks)

    assert verify_checks.main(["--project", str(project), "--plugin-root", str(plugin_root)]) == 0


def test_check_output_with_invalid_utf8_is_recorded_normally(project: Path) -> None:
    (project / ".harnex.yml").write_text(
        CHOICES.format(check_command=r"printf '\377\376'"), encoding="utf-8"
    )

    assert verify_checks.main(["--project", str(project)]) == 0

    facts_file = next((project / ".harnex" / "state" / "verify").glob("*.json"))
    facts = json.loads(facts_file.read_text(encoding="utf-8"))
    assert facts["exit_status"] == 0
    assert "\ufffd" in facts["output"]
