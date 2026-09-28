#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Report any path written or modified outside a change's own directory.

Pillar 5's detection for the `sdd` rule "treat the proposal as the boundary of the
change" (`the-proposal-is-the-scope`): `propose` snapshots `git status --porcelain=v1`
before it starts, and once every required artifact exists this script diffs a fresh
snapshot against it. It reports; it never fails the run on what it finds and never undoes
a write — only a script error (not a git repository, an unreadable snapshot) exits
non-zero, so the caller can tell "nothing to report" from "the check itself did not run".

    uv run plugin/feedback/scope_check.py check --change <name> --before <snapshot-file> \\
        --project <project root>

Standard library only.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _parse_porcelain(text: str) -> set[str]:
    """Every path `git status --porcelain=v1` names, tracked or not. The status code in
    the first two columns is not read; a path being reported at all is enough."""
    paths = set()
    for line in text.splitlines():
        if not line.strip():
            continue
        path = line[3:]
        if " -> " in path:  # a rename: only the new path is this run's concern
            path = path.split(" -> ", 1)[1]
        paths.add(path)
    return paths


def _status_text(project: Path) -> str:
    result = subprocess.run(
        # `--untracked-files=all` so a brand-new directory is listed file by file,
        # not collapsed to its own top-level entry — the change's own directory is
        # exactly that kind of new directory on the run this check matters for.
        ["git", "-C", str(project), "status", "--porcelain=v1", "--untracked-files=all"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def scope_violations(project: Path, change: str, before_text: str) -> list[str]:
    """Paths new since `before_text` was captured that do not sit under the change's own
    directory. A path already dirty before the snapshot was taken is never reported,
    whatever state it is in now — it predates this proposal."""
    before = _parse_porcelain(before_text)
    after = _parse_porcelain(_status_text(project))
    prefix = f"openspec/changes/{change}/"
    return sorted(path for path in (after - before) if not path.startswith(prefix))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report any path written or modified outside a change's own directory."
    )
    parser.add_argument("verb", choices=("check",))
    parser.add_argument("--change", required=True, help="the change's own directory name")
    parser.add_argument(
        "--before", required=True, type=Path,
        help="a `git status --porcelain=v1` snapshot taken before the run started",
    )
    parser.add_argument("--project", default=".", help="the project to check")
    args = parser.parse_args(argv)

    project = Path(args.project).resolve()
    try:
        before_text = args.before.read_text(encoding="utf-8")
        violations = scope_violations(project, args.change, before_text)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"scope-check: {error}", file=sys.stderr)
        return 1

    if not violations:
        print("Nothing was written outside the change's own directory.")
    else:
        print("Written outside the change's own directory:")
        for path in violations:
            print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
