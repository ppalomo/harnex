#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Run a project's configured check and record the resulting verification facts.

    uv run plugin/scripts/verify_checks.py --project <root> [--base HEAD] [--plugin-root <root>]

The check command is read from the project's `.harnex.yml`.  Its exit status does not
prevent the facts from being written: a failed check is verification evidence too.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import setup as setup_script
from working_tree import tree_fingerprint


class VerifyChecksError(Exception):
    """The project's configured verification check cannot be run."""


INTERNAL_ERROR_SENTINEL = "verify-checks: internal-error: no facts file was written:"


def run_playwright_checks(project: Path) -> dict[str, object]:
    """Collect UI verification findings for a running project application.

    Playwright MCP setup is intentionally outside this script for now.  Keeping this
    boundary small lets the configured MCP client replace the placeholder without
    changing how verification facts are recorded.
    """
    del project
    return {
        "status": "not_configured",
        "reason": "Playwright MCP is not configured for this project",
    }


def facts_directory(project: Path) -> Path:
    return project / ".harnex" / "state" / "verify"


def write_facts(project: Path, facts: dict[str, object]) -> Path:
    """Atomically write one immutable record for this check invocation."""
    directory = facts_directory(project)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{time.time_ns()}-{os.getpid()}.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(facts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return path


def run_check(project: Path, base_ref: str, plugin_root: Path) -> tuple[Path, dict[str, object]]:
    """Run the recorded command and save its result against the tree it leaves behind."""
    choices_path = project / setup_script.CHOICES
    try:
        choices = setup_script.parse_choices(
            choices_path.read_text(encoding="utf-8"), str(choices_path)
        )
    except (OSError, setup_script.SetupError) as error:
        raise VerifyChecksError(f"could not read {choices_path}: {error}") from error

    check_command = choices.get("check_command")
    if not isinstance(check_command, str) or not check_command.strip():
        raise VerifyChecksError(f"{choices_path} must define a non-empty check_command")
    profiles = choices["profiles"]
    completed = subprocess.run(
        check_command,
        cwd=project,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        check=False,
    )
    fingerprint = tree_fingerprint(project, base_ref)
    facts: dict[str, object] = {
        "base_ref": base_ref,
        "check_command": check_command,
        "exit_status": completed.returncode,
        "output": completed.stdout,
        "fingerprint": fingerprint,
    }
    if isinstance(profiles, list) and any(
        profile in setup_script.ui_profiles(plugin_root) for profile in profiles
    ):
        facts["playwright"] = run_playwright_checks(project)
    else:
        facts["playwright"] = {
            "status": "skipped",
            "reason": "no UI profile declared",
        }
    return write_facts(project, facts), facts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="run and record the project's verification check")
    parser.add_argument("--project", default=".")
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--plugin-root", default=None, help="where the harness is installed")
    args = parser.parse_args(argv)

    plugin_root = (
        Path(args.plugin_root).resolve() if args.plugin_root else setup_script.default_plugin_root()
    )

    try:
        path, facts = run_check(Path(args.project).resolve(), args.base, plugin_root)
    except Exception as error:
        print(f"{INTERNAL_ERROR_SENTINEL} {error}", file=sys.stderr)
        return 1

    print(json.dumps({"facts_file": str(path), **facts}))
    return int(facts["exit_status"])


if __name__ == "__main__":
    raise SystemExit(main())
