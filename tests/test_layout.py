"""The plugin's layout is the five pillars.

A component that lands in the wrong directory is cheap to move today and expensive to
move once something imports it, so the boundary is a test rather than a convention.

Verified against Claude Code 2.1.267: the host directory list below is outside our
control and is the one thing here that a host upgrade can invalidate.
"""

from pathlib import Path

import pytest

PILLARS = {
    "context": 1,
    "tools": 2,
    "orchestration": 3,
    "control": 4,
    "feedback": 5,
}

# Directories the host itself reads. What they contain still belongs to one pillar.
HOST_DIRECTORIES = {
    ".claude-plugin",
    "commands",
    "skills",
    "agents",
    "hooks",
    "scripts",
}


def _directories(plugin_root: Path) -> set[str]:
    return {d.name for d in plugin_root.iterdir() if d.is_dir()}


def test_every_directory_is_a_pillar_or_a_host_directory(plugin_root: Path) -> None:
    allowed = set(PILLARS) | HOST_DIRECTORIES
    stray = sorted(_directories(plugin_root) - allowed)
    assert not stray, (
        f"{stray} is neither a pillar nor a directory the host reads. "
        "Every component lives in exactly one pillar; if it seems to belong to two, "
        "it is two components."
    )


def test_all_five_pillars_are_present(plugin_root: Path) -> None:
    missing = sorted(set(PILLARS) - _directories(plugin_root))
    assert not missing, f"missing pillar directories: {missing}"


@pytest.mark.parametrize("pillar", sorted(PILLARS))
def test_each_pillar_states_what_it_holds(plugin_root: Path, pillar: str) -> None:
    readme = plugin_root / pillar / "README.md"
    assert readme.is_file(), f"pillar {pillar} has no README.md stating what it holds"

    text = readme.read_text(encoding="utf-8")
    assert f"# Pillar {PILLARS[pillar]}" in text, (
        f"{readme} does not name its pillar number"
    )
    assert "## What belongs here" in text, f"{readme} does not say what belongs in it"
    assert "## What does not" in text, f"{readme} does not say what does not"


def test_a_stray_directory_is_detected(plugin_root: Path, tmp_path: Path) -> None:
    """The check fails on a tree it should reject, not only passes on a good one."""
    stray = plugin_root / "utils"
    stray.mkdir()
    try:
        with pytest.raises(AssertionError, match="utils"):
            test_every_directory_is_a_pillar_or_a_host_directory(plugin_root)
    finally:
        stray.rmdir()


def test_a_pillar_without_its_readme_is_detected(plugin_root: Path) -> None:
    readme = plugin_root / "control" / "README.md"
    kept = readme.read_text(encoding="utf-8")
    readme.unlink()
    try:
        with pytest.raises(AssertionError, match="no README.md"):
            test_each_pillar_states_what_it_holds(plugin_root, "control")
    finally:
        readme.write_text(kept, encoding="utf-8")
