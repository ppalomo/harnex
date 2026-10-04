"""Tests for detecting the plugin's own identity and version-bump candidates."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import version_bump

requires_uv = pytest.mark.skipif(shutil.which("uv") is None, reason="uv is how the host runs this script")


@pytest.fixture
def project(tmp_path: Path) -> Path:
    path = tmp_path / "project"
    path.mkdir()
    return path


def _write_json(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content), encoding="utf-8")


def _marketplace_path(project: Path) -> Path:
    return project / ".claude-plugin" / "marketplace.json"


def _manifest_path(project: Path, source: str = "plugin") -> Path:
    return project / source / ".claude-plugin" / "plugin.json"


def _write_pair(
    project: Path,
    *,
    entry_name: str = "harnex",
    entry_version: str = "1.2.3",
    manifest_name: str = "harnex",
    manifest_version: str = "1.2.3",
    source: str = "./plugin",
) -> None:
    _write_json(
        _marketplace_path(project),
        {
            "plugins": [
                {"name": entry_name, "source": source, "version": entry_version},
            ],
        },
    )
    _write_json(_manifest_path(project), {"name": manifest_name, "version": manifest_version})


def test_no_marketplace_file_is_reported(project: Path) -> None:
    result = version_bump.detect(project)

    assert result == {"found": False, "reason": "no marketplace.json found"}


def test_zero_entries_is_reported(project: Path) -> None:
    _write_json(_marketplace_path(project), {"plugins": []})

    result = version_bump.detect(project)

    assert result == {
        "found": False,
        "reason": "expected exactly one plugin entry, found 0",
    }


def test_multiple_entries_is_reported(project: Path) -> None:
    _write_json(
        _marketplace_path(project),
        {
            "plugins": [
                {"name": "harnex", "source": "./plugin", "version": "1.0.0"},
                {"name": "other", "source": "./other", "version": "1.0.0"},
            ],
        },
    )

    result = version_bump.detect(project)

    assert result == {
        "found": False,
        "reason": "expected exactly one plugin entry, found 2",
    }


def test_unresolved_source_is_reported(project: Path) -> None:
    _write_json(
        _marketplace_path(project),
        {"plugins": [{"name": "harnex", "source": "./missing", "version": "1.0.0"}]},
    )
    # The real plugin manifest lives under "./plugin", not "./missing".
    _write_json(_manifest_path(project), {"name": "harnex", "version": "1.0.0"})

    result = version_bump.detect(project)

    assert result == {"found": False, "reason": "an unresolved plugin source"}


def test_disagreeing_manifests_is_reported(project: Path) -> None:
    _write_pair(project, entry_version="1.0.0", manifest_version="2.0.0")

    result = version_bump.detect(project)

    assert result == {
        "found": False,
        "reason": "the marketplace entry and the plugin manifest disagree",
    }


def test_agreeing_manifests_are_found_with_candidate_versions(project: Path) -> None:
    _write_pair(project, entry_version="1.2.3", manifest_version="1.2.3")

    result = version_bump.detect(project)

    assert result == {
        "found": True,
        "marketplace_path": _marketplace_path(project),
        "manifest_path": _manifest_path(project),
        "name": "harnex",
        "current_version": "1.2.3",
        "candidates": {"patch": "1.2.4", "minor": "1.3.0", "major": "2.0.0"},
    }


def _write_indented_pair(project: Path) -> None:
    """Write a manifest/marketplace pair formatted like the real repo's own files.

    Multi-line, two-space-indented JSON, so a test can tell which single line a
    write touched. The marketplace's own ``metadata.version`` is deliberately a
    different value than the plugin's version, so a test can tell the two apart.
    """
    manifest = {
        "name": "harnex",
        "version": "1.2.3",
        "description": "A reusable harness for AI coding agents.",
        "author": {"name": "A. Developer", "url": "https://example.com/a"},
        "license": "MIT",
        "keywords": ["harness", "agents"],
    }
    marketplace = {
        "name": "harnex",
        "owner": {"name": "A. Developer", "url": "https://example.com/a"},
        "metadata": {"description": "The harnex marketplace.", "version": "9.9.9"},
        "plugins": [
            {
                "name": "harnex",
                "source": "./plugin",
                "description": "A reusable harness for AI coding agents.",
                "version": "1.2.3",
                "license": "MIT",
                "homepage": "https://example.com/a",
                "keywords": ["harness", "agents"],
            }
        ],
    }
    manifest_path = _manifest_path(project)
    marketplace_path = _marketplace_path(project)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    marketplace_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    marketplace_path.write_text(json.dumps(marketplace, indent=2) + "\n", encoding="utf-8")


@pytest.mark.parametrize(
    ("level", "expected"),
    [("patch", "1.2.4"), ("minor", "1.3.0"), ("major", "2.0.0")],
)
def test_bump_changes_only_the_version_line(project: Path, level: str, expected: str) -> None:
    _write_indented_pair(project)
    manifest_path = _manifest_path(project)
    marketplace_path = _marketplace_path(project)
    original_manifest_lines = manifest_path.read_text(encoding="utf-8").splitlines()
    original_marketplace_lines = marketplace_path.read_text(encoding="utf-8").splitlines()

    result = version_bump.bump(project, level)

    assert result == expected
    new_manifest_lines = manifest_path.read_text(encoding="utf-8").splitlines()
    new_marketplace_lines = marketplace_path.read_text(encoding="utf-8").splitlines()

    assert len(new_manifest_lines) == len(original_manifest_lines)
    manifest_changes = [
        index
        for index, (old, new) in enumerate(zip(original_manifest_lines, new_manifest_lines))
        if old != new
    ]
    assert len(manifest_changes) == 1
    assert '"version"' in new_manifest_lines[manifest_changes[0]]
    assert expected in new_manifest_lines[manifest_changes[0]]
    assert "1.2.3" in original_manifest_lines[manifest_changes[0]]

    assert len(new_marketplace_lines) == len(original_marketplace_lines)
    marketplace_changes = [
        index
        for index, (old, new) in enumerate(zip(original_marketplace_lines, new_marketplace_lines))
        if old != new
    ]
    assert len(marketplace_changes) == 1
    assert '"version"' in new_marketplace_lines[marketplace_changes[0]]
    assert expected in new_marketplace_lines[marketplace_changes[0]]
    assert "1.2.3" in original_marketplace_lines[marketplace_changes[0]]


def test_bump_does_not_touch_marketplace_metadata_version(project: Path) -> None:
    _write_indented_pair(project)

    version_bump.bump(project, "patch")

    marketplace = json.loads(_marketplace_path(project).read_text(encoding="utf-8"))
    assert marketplace["metadata"]["version"] == "9.9.9"


# --- the CLI, run as a real process ------------------------------------------------------


@requires_uv
def test_detect_cli_prints_detect_result_and_exits_zero(project: Path, repo_root: Path) -> None:
    _write_pair(project, entry_version="1.2.3", manifest_version="1.2.3")
    script = repo_root / "plugin" / "scripts" / "version_bump.py"

    finished = subprocess.run(
        ["uv", "run", "--quiet", str(script), "detect", "--project", str(project)],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert finished.returncode == 0, finished.stderr
    result = json.loads(finished.stdout)
    assert result == {
        "found": True,
        "marketplace_path": str(_marketplace_path(project)),
        "manifest_path": str(_manifest_path(project)),
        "name": "harnex",
        "current_version": "1.2.3",
        "candidates": {"patch": "1.2.4", "minor": "1.3.0", "major": "2.0.0"},
    }


@requires_uv
def test_bump_cli_prints_name_and_versions_and_exits_zero(project: Path, repo_root: Path) -> None:
    _write_indented_pair(project)
    script = repo_root / "plugin" / "scripts" / "version_bump.py"

    finished = subprocess.run(
        ["uv", "run", "--quiet", str(script), "bump", "--project", str(project), "--level", "patch"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert finished.returncode == 0, finished.stderr
    result = json.loads(finished.stdout)
    assert result == {"name": "harnex", "from_version": "1.2.3", "to_version": "1.2.4"}
    manifest = json.loads(_manifest_path(project).read_text(encoding="utf-8"))
    assert manifest["version"] == "1.2.4"


@requires_uv
def test_bump_cli_exits_one_with_json_error_when_detect_fails(project: Path, repo_root: Path) -> None:
    script = repo_root / "plugin" / "scripts" / "version_bump.py"

    finished = subprocess.run(
        ["uv", "run", "--quiet", str(script), "bump", "--project", str(project), "--level", "patch"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert finished.returncode == 1, finished.stdout
    result = json.loads(finished.stdout)
    assert result == {"error": "cannot bump: no marketplace.json found"}
