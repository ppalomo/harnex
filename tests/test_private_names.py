"""Nothing published inside the plugin names a project or a private resource.

The check has two halves, because a committed denylist of private names would publish
the private names it forbids:

- The **shape half**, committed here: patterns that are private by construction — things
  that look like credentials, absolute paths under someone's home directory, private host
  suffixes. Anyone can run it.
- The **personal half**, never committed: a file of literal terms — project names, domain
  vocabulary, internal hosts — found through the ``HARNEX_DENYLIST`` environment
  variable. It skips itself when the variable is unset, so a stranger's run is visibly
  weaker than the owner's rather than silently weaker.

The owner's run, with both halves, is the gate before publishing.
"""

import os
import re
from pathlib import Path

import pytest

DENYLIST_ENV_VAR = "HARNEX_DENYLIST"

# Shapes that are private by construction. Each entry is (name, pattern).
SHAPE_PATTERNS: list[tuple[str, str]] = [
    ("OpenAI-style key", r"\bsk-[A-Za-z0-9_-]{16,}"),
    ("GitHub token", r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    ("AWS access key id", r"\bAKIA[0-9A-Z]{16}\b"),
    ("Slack token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ("private key block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("assigned secret", r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    ("home directory path", r"/(?:Users|home)/[A-Za-z0-9._-]+/"),
    ("private host suffix", r"\b[A-Za-z0-9-]+\.(?:internal|corp|lan|intranet)\b"),
    ("bearer header", r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._-]{12,}"),
]

TEXT_SUFFIXES = {
    ".md", ".json", ".yaml", ".yml", ".py", ".toml", ".txt", ".sh", ".ini", ".cfg", ""
}


def _published_files(plugin_root: Path) -> list[Path]:
    """Every file that lands on a machine when the plugin is installed."""
    return [
        p
        for p in sorted(plugin_root.rglob("*"))
        if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES
    ]


def _scan(files: list[Path], patterns: list[tuple[str, str]]) -> list[str]:
    hits: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for name, pattern in patterns:
                if re.search(pattern, line):
                    hits.append(f"{path}:{lineno}: {name}")
    return hits


def test_the_plugin_publishes_no_private_shape(plugin_root: Path) -> None:
    hits = _scan(_published_files(plugin_root), SHAPE_PATTERNS)
    assert not hits, "private-looking content in the plugin:\n" + "\n".join(hits)


def _personal_patterns() -> list[tuple[str, str]]:
    """The owner's half. Skips, visibly, when the personal list is not available."""
    location = os.environ.get(DENYLIST_ENV_VAR)
    if not location:
        pytest.skip(
            f"{DENYLIST_ENV_VAR} is not set: the shape half ran, the personal half did "
            "not. Point it at a file of one term per line before publishing."
        )

    denylist = Path(location).expanduser()
    assert denylist.is_file(), f"{DENYLIST_ENV_VAR} points at {denylist}, which is not a file"

    terms = [
        line.strip()
        for line in denylist.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert terms, f"{denylist} lists no terms"
    return [("personal term", re.escape(term)) for term in terms]


def test_the_plugin_publishes_no_personal_term(plugin_root: Path) -> None:
    hits = _scan(_published_files(plugin_root), _personal_patterns())
    assert not hits, "private names in the plugin:\n" + "\n".join(hits)


def _rendered(tmp_path: Path, rules_dir: Path) -> list[Path]:
    """Every rule the harness holds, rendered as a project would receive it.

    The tree is checked above, but what reaches a project is the rendering, and a
    renderer is free to add prose of its own. This checks the thing that travels.
    """
    import render_rules

    document = render_rules.render(render_rules.available_sets(rules_dir), [], rules_dir)
    path = tmp_path / "rules.md"
    path.write_text(document, encoding="utf-8")
    return [path]


def test_the_rendered_rules_publish_no_private_shape(tmp_path: Path, rules_dir: Path) -> None:
    hits = _scan(_rendered(tmp_path, rules_dir), SHAPE_PATTERNS)
    assert not hits, "private-looking content in the rendered rules:\n" + "\n".join(hits)


def test_the_rendered_rules_publish_no_personal_term(tmp_path: Path, rules_dir: Path) -> None:
    hits = _scan(_rendered(tmp_path, rules_dir), _personal_patterns())
    assert not hits, "private names in the rendered rules:\n" + "\n".join(hits)


def test_a_seeded_secret_is_detected(plugin_root: Path) -> None:
    """The check fails on a tree it should reject, not only passes on a good one."""
    seeded = plugin_root / "context" / "seeded-for-the-test.md"
    seeded.write_text("token = " + "A" * 24 + "\n", encoding="utf-8")
    try:
        with pytest.raises(AssertionError, match="assigned secret"):
            test_the_plugin_publishes_no_private_shape(plugin_root)
    finally:
        seeded.unlink()


def test_a_seeded_home_path_is_detected(plugin_root: Path) -> None:
    seeded = plugin_root / "context" / "seeded-for-the-test.md"
    seeded.write_text("see /Users/someone/Developer/a-project/notes.md\n", encoding="utf-8")
    try:
        with pytest.raises(AssertionError, match="home directory path"):
            test_the_plugin_publishes_no_private_shape(plugin_root)
    finally:
        seeded.unlink()


def _written(tmp_path: Path, plugin_root: Path) -> list[Path]:
    """A project as setup leaves it: the other thing that travels out of the harness.

    The tree and the rendered rules are checked above; this is everything else setup puts
    in someone's repository — the templates it renders and the floor it merges.
    """
    import json

    import setup

    project = tmp_path / "written"
    project.mkdir()
    from conftest import DEFAULT_ANSWERS

    answers = setup.read_answers(json.dumps(DEFAULT_ANSWERS), plugin_root)
    setup.apply_plan(setup.build_plan(project, plugin_root, answers))
    return [p for p in sorted(project.rglob("*")) if p.is_file()]


def test_what_setup_writes_publishes_no_private_shape(tmp_path: Path, plugin_root: Path) -> None:
    hits = _scan(_written(tmp_path, plugin_root), SHAPE_PATTERNS)
    assert not hits, "private-looking content in what setup writes:\n" + "\n".join(hits)


def test_what_setup_writes_publishes_no_personal_term(tmp_path: Path, plugin_root: Path) -> None:
    hits = _scan(_written(tmp_path, plugin_root), _personal_patterns())
    assert not hits, "private names in what setup writes:\n" + "\n".join(hits)


def _snapshots(repo_root: Path) -> list[Path]:
    """The committed snapshots: a leak recorded here would be published with the tests."""
    return [p for p in sorted((repo_root / "tests" / "snapshots").rglob("*")) if p.is_file()]


def test_the_snapshots_publish_no_private_shape(repo_root: Path) -> None:
    hits = _scan(_snapshots(repo_root), SHAPE_PATTERNS)
    assert not hits, "private-looking content in a snapshot:\n" + "\n".join(hits)


def test_the_snapshots_publish_no_personal_term(repo_root: Path) -> None:
    hits = _scan(_snapshots(repo_root), _personal_patterns())
    assert not hits, "private names in a snapshot:\n" + "\n".join(hits)
