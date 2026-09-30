"""Shared facts about a project's Git working tree."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


def tree_fingerprint(project: Path, base_ref: str) -> str:
    """Return the working tree's content fingerprint relative to ``base_ref``.

    Besides the Git diff, the fingerprint contains the sorted names and contents of
    untracked files.  It deliberately describes the tree, not a commit.
    """
    diff = subprocess.run(
        ["git", "-C", str(project), "diff", base_ref],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    status = subprocess.run(
        ["git", "-C", str(project), "status", "--porcelain=v1", "--untracked-files=all"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    untracked = sorted(line[3:] for line in status.splitlines() if line.startswith("??"))

    hasher = hashlib.sha256()
    hasher.update(diff.encode("utf-8"))
    for path in untracked:
        hasher.update(path.encode("utf-8"))
        file_path = project / path
        if file_path.is_file():
            hasher.update(file_path.read_bytes())
    return hasher.hexdigest()
