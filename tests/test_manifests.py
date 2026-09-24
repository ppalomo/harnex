"""Both manifests declare an identity and pass strict validation.

Strict validation treats warnings as errors, so the field list is not decoration: without
``author`` in the plugin manifest and a description in the marketplace metadata, strict
fails. Measured against Claude Code 2.1.267.

The validation itself needs the host CLI, which a fresh checkout or a CI runner may not
have, so those two tests skip themselves when it is absent. The field checks below do
not need it and always run.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

CLI = "claude"
TIMEOUT_SECONDS = 120

requires_cli = pytest.mark.skipif(
    shutil.which(CLI) is None,
    reason=f"{CLI} is not on PATH: the manifests were checked for their fields, not validated",
)


def _manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(repo_root: Path, target: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [CLI, "plugin", "validate", target, "--strict"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )


def test_plugin_manifest_declares_its_identity(plugin_root: Path) -> None:
    manifest = _manifest(plugin_root / ".claude-plugin" / "plugin.json")

    assert manifest["name"] == "harnex"
    assert manifest["version"].count(".") == 2, "version is not semantic"
    assert manifest["description"].strip()
    # Without an author, --strict fails on a warning.
    assert manifest["author"]["name"].strip()


def test_marketplace_lists_exactly_one_plugin(repo_root: Path) -> None:
    manifest = _manifest(repo_root / ".claude-plugin" / "marketplace.json")

    # Without a description, --strict fails on a warning.
    assert manifest["metadata"]["description"].strip()
    assert len(manifest["plugins"]) == 1, "the catalogue holds one plugin: the harness"

    entry = manifest["plugins"][0]
    assert entry["name"] == "harnex"
    assert entry["source"] == "./plugin", (
        "the plugin is nested so that the docs, the diagrams and this repository's own "
        "specs are not installed onto every machine"
    )


def test_the_marketplace_entry_and_the_plugin_agree(repo_root: Path, plugin_root: Path) -> None:
    entry = _manifest(repo_root / ".claude-plugin" / "marketplace.json")["plugins"][0]
    plugin = _manifest(plugin_root / ".claude-plugin" / "plugin.json")

    assert entry["name"] == plugin["name"]
    assert entry["version"] == plugin["version"]


@requires_cli
def test_the_plugin_manifest_passes_strict(repo_root: Path) -> None:
    result = _validate(repo_root, "plugin")
    assert result.returncode == 0, result.stdout + result.stderr


@requires_cli
def test_the_marketplace_manifest_passes_strict(repo_root: Path) -> None:
    result = _validate(repo_root, ".")
    assert result.returncode == 0, result.stdout + result.stderr
