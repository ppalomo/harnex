"""The canary check, started the way the host actually starts it: as its own process,
running the exact command `plugin/hooks/hooks.json` declares, not imported.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path

import pytest

WORD = "Hullaballoo!"

CHOICES = """\
project_name: scratch
profiles:
sets:
  - canary
features:
canary: {word}
decision_model: mock
check_command: make check
""".format(word=WORD)


def _hook_command(plugin_root: Path) -> tuple[list[str], int]:
    """The `Stop` hook's command and declared timeout, read from the plugin's own
    manifest rather than restated here, so the two cannot drift apart unnoticed."""
    declared = json.loads((plugin_root / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    hook = declared["hooks"]["Stop"][0]["hooks"][0]
    assert hook["type"] == "command"
    command = hook["command"].replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_root))
    return shlex.split(command), hook["timeout"]


def _run_hook(
    plugin_root: Path, project: Path, payload: dict
) -> subprocess.CompletedProcess[str]:
    argv, timeout = _hook_command(plugin_root)
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(project)
    start = time.monotonic()
    finished = subprocess.run(
        argv,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout + 10,  # generous ceiling for the test itself; the assertion below is the real one
    )
    elapsed = time.monotonic() - start
    assert elapsed < timeout, (
        f"the hook took {elapsed:.1f}s, close to or over its declared {timeout}s timeout"
    )
    return finished


requires_uv = pytest.mark.skipif(
    shutil.which("uv") is None, reason="uv is how the host runs the hook"
)


@requires_uv
def test_word_present(tmp_path: Path, plugin_root: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".harnex.yml").write_text(CHOICES, encoding="utf-8")

    finished = _run_hook(
        plugin_root, project, {"last_assistant_message": f"All done. {WORD}"}
    )
    assert finished.returncode == 0
    assert finished.stdout.strip() == ""


@requires_uv
def test_word_missing(tmp_path: Path, plugin_root: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".harnex.yml").write_text(CHOICES, encoding="utf-8")

    finished = _run_hook(
        plugin_root, project, {"last_assistant_message": "All done, no word here."}
    )
    assert finished.returncode == 0
    message = json.loads(finished.stdout)
    assert "decision" not in message
    assert WORD in message["systemMessage"]


@requires_uv
def test_no_harnex_yml(tmp_path: Path, plugin_root: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    finished = _run_hook(
        plugin_root, project, {"last_assistant_message": "All done, no word here."}
    )
    assert finished.returncode == 0
    assert finished.stdout.strip() == ""
