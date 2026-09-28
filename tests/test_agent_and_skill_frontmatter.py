"""Agents and skills use the minimum frontmatter (`AGENTS.md`), and a role's Claude Code
adapter states its role prompt exactly once, even though the host gives an agent's body no
way to import another file — so the correspondence is a test, not an assumption.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

AGENT_FIELDS = {"name", "description", "tools"}
SKILL_FIELDS = {"name", "description"}

_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
_FIELD = re.compile(r"^([a-z]+): *(.*)$")


def _read(path: Path) -> tuple[dict[str, str], str]:
    match = _FRONTMATTER.match(path.read_text(encoding="utf-8"))
    assert match, f"{path}: does not open with a frontmatter block"
    fields: dict[str, str] = {}
    for line in match.group(1).split("\n"):
        field = _FIELD.match(line)
        assert field, f"{path}: {line!r} is not a `key: value` frontmatter line"
        fields[field.group(1)] = field.group(2)
    return fields, match.group(2)


def _tools(fields: dict[str, str]) -> list[str]:
    return [tool.strip() for tool in fields["tools"].split(",") if tool.strip()]


AGENT_FILES = sorted((Path(__file__).resolve().parent.parent / "plugin" / "agents").glob("*.md"))
SKILL_FILES = sorted((Path(__file__).resolve().parent.parent / "plugin" / "skills").glob("*/SKILL.md"))


def test_there_is_at_least_one_agent() -> None:
    assert AGENT_FILES, "no agent files under plugin/agents/"


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_an_agent_has_exactly_the_minimum_frontmatter(path: Path) -> None:
    fields, _ = _read(path)
    assert set(fields) == AGENT_FIELDS, (
        f"{path}: frontmatter is {sorted(fields)}, expected exactly {sorted(AGENT_FIELDS)}"
    )
    assert fields["name"] == path.stem


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_the_verifier_role_cannot_write(path: Path) -> None:
    if path.stem != "verifier":
        pytest.skip("only the verifier is read-only by role")
    fields, _ = _read(path)
    tools = _tools(fields)
    forbidden = {"Edit", "Write", "Bash"} & set(tools)
    assert not forbidden, f"{path}: declares {forbidden}, which a read-only role must not have"


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_the_agent_states_its_role_exactly_once(path: Path, plugin_root: Path) -> None:
    """The host gives an agent's body no way to import another file (verified against
    Claude Code's own docs while designing `C2`), so the adapter's body is a copy of the
    role prompt it binds — and this is what makes the copy provably exact, not assumed."""
    role_path = plugin_root / "orchestration" / "roles" / f"{path.stem}.md"
    assert role_path.is_file(), f"{path}: no role prompt at {role_path} for it to bind"
    _, body = _read(path)
    role_text = role_path.read_text(encoding="utf-8")
    assert body.strip() == role_text.strip(), (
        f"{path} and {role_path} have drifted apart — the adapter's body must be an exact "
        "copy of the role prompt it binds"
    )


def test_there_is_at_least_one_skill() -> None:
    assert SKILL_FILES, "no skills under plugin/skills/"


@pytest.mark.parametrize("path", SKILL_FILES, ids=lambda p: p.parent.name)
def test_a_skill_has_exactly_the_minimum_frontmatter(path: Path) -> None:
    fields, _ = _read(path)
    assert set(fields) == SKILL_FIELDS, (
        f"{path}: frontmatter is {sorted(fields)}, expected exactly {sorted(SKILL_FIELDS)}"
    )
    assert fields["name"] == path.parent.name, f"{path}: name must equal the skill's directory name"
