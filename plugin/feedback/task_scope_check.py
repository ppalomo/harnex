"""Detect whether a builder's write stayed inside its task's own scope, and whether it
touched a protected path — pillar 5's detection for the `code` rule
`no-scope-beyond-the-task` and the `sdd` rule `builders-never-tick-tasks`.

Both checks are pure comparisons over two `git status --porcelain=v1
--untracked-files=all` snapshots (C2's `scope_check.py` technique, reused): one taken
before a builder ran, one after. Neither check runs `git` itself — the caller (`apply`'s
loop) already takes the fingerprinting snapshot for other reasons and passes the text
straight through, so there is exactly one place per task that shells out to `git status`.

There is no CLI here: only `plugin/scripts/apply_loop.py` calls this module, and it
imports it directly, the way `decide.py` already imports `setup.py` (C2).

Standard library only.
"""

from __future__ import annotations

PROTECTED_PREFIXES = ("openspec/", ".harnex/")


def parse_porcelain(text: str) -> set[str]:
    """Every path `git status --porcelain=v1 --untracked-files=all` names, tracked or
    not. The status code in the first two columns is not read; a path being reported at
    all is enough."""
    paths = set()
    for line in text.splitlines():
        if not line.strip():
            continue
        path = line[3:]
        if " -> " in path:  # a rename: only the new path is this run's concern
            path = path.split(" -> ", 1)[1]
        paths.add(path)
    return paths


def changed_paths(before_text: str, after_text: str) -> set[str]:
    return parse_porcelain(after_text) - parse_porcelain(before_text)


def _in_declared_scope(path: str, declared: list[str]) -> bool:
    for allowed in declared:
        allowed = allowed.rstrip("/")
        if path == allowed or path.startswith(f"{allowed}/"):
            return True
    return False


def check_declared(task_paths: list[str], before_text: str, after_text: str) -> list[str]:
    """Every changed path that falls outside the task's own declared paths. Empty means
    everything the builder touched sits inside what the task named."""
    changed = changed_paths(before_text, after_text)
    return sorted(path for path in changed if not _in_declared_scope(path, task_paths))


def check_protected(before_text: str, after_text: str) -> list[str]:
    """Every changed path under `openspec/` or `.harnex/` — refused regardless of what
    the task declared. Empty means neither protected path was touched."""
    changed = changed_paths(before_text, after_text)
    return sorted(path for path in changed if path.startswith(PROTECTED_PREFIXES))
