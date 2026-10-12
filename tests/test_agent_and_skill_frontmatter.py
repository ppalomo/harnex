"""Agents and skills use the minimum frontmatter (`AGENTS.md`), a role states its name,
description, tools and phase once in its own frontmatter, and a role's Claude Code adapter
is the rendering of that role by `render_agents.py sync`, even though the host gives an
agent's body no way to import another file — so the correspondence is a check that
`sync --check` is clean, not an assumption.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pytest
import render_agents

AGENT_FIELDS = {"name", "description", "tools"}
SKILL_FIELDS = {"name", "description"}
ROLE_FIELDS = {"name", "description", "tools", "phase"}
PHASES = {"apply", "propose", "review", "verify"}

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
ROLE_FILES = sorted(
    (Path(__file__).resolve().parent.parent / "plugin" / "orchestration" / "roles").glob("*.md")
)


def test_there_is_at_least_one_agent() -> None:
    assert AGENT_FILES, "no agent files under plugin/agents/"


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_an_agent_has_exactly_the_minimum_frontmatter(path: Path) -> None:
    fields, _ = _read(path)
    assert set(fields) == AGENT_FIELDS, (
        f"{path}: frontmatter is {sorted(fields)}, expected exactly {sorted(AGENT_FIELDS)}"
    )
    assert fields["name"] == path.stem


# The tools that let an agent write a file or run a command; a role that only reads
# declares none of them, and neither does any agent that binds such a role.
WRITING_TOOLS = {"Edit", "Write", "Bash"}
# The one phase whose roles write: `builder` and `test-engineer` are skipped, not checked.
WRITING_PHASE = "apply"


def _role_of(path: Path) -> Path:
    """The role a file states: itself for a role, the role it binds for an agent."""
    if path.parent.name == "roles":
        return path
    return path.parent.parent / "orchestration" / "roles" / f"{path.stem}.md"


@pytest.mark.parametrize(
    "path", ROLE_FILES + AGENT_FILES, ids=lambda p: f"{p.parent.name}-{p.stem}"
)
def test_the_read_only_roles_cannot_write(path: Path) -> None:
    """Every role whose phase is `review`, `propose` or `verify` reads and nothing else,
    so it — and any agent bound to it — declares no editing, writing or command tool."""
    role_path = _role_of(path)
    assert role_path.is_file(), f"{path}: no role prompt at {role_path} to read the phase from"
    role_fields, _ = _read(role_path)
    if role_fields["phase"] == WRITING_PHASE:
        pytest.skip(f"{path.stem} serves the {WRITING_PHASE} phase, which writes by role")
    fields, _ = _read(path)
    forbidden = WRITING_TOOLS & set(_tools(fields))
    assert not forbidden, (
        f"{path}: declares {sorted(forbidden)}, which a {role_fields['phase']}-phase role "
        "must not have"
    )


def test_every_agent_is_the_rendering_of_its_role(plugin_root: Path) -> None:
    """The host gives an agent's body no way to import another file (verified against
    Claude Code's own docs while designing `C2`, and again for `agent-teams`), so each
    adapter holds its role's text — as the output of `render_agents.py sync`: `name`,
    `description` and `tools` copied, `phase` dropped, the body whole. The same check
    `sync --check` makes, in-process, so an edited role with a stale adapter and a
    hand-edited adapter fail the same way and the fix is the same command."""
    stale = render_agents.sync(plugin_root, check=True)
    assert not stale, (
        f"stale adapter(s) under plugin/agents/: {', '.join(stale)} — each differs from "
        "the rendering of its role; run `uv run plugin/scripts/render_agents.py sync`"
    )


def test_there_is_at_least_one_role() -> None:
    assert ROLE_FILES, "no role files under plugin/orchestration/roles/"


@pytest.mark.parametrize("path", ROLE_FILES, ids=lambda p: p.stem)
def test_a_role_has_exactly_the_four_fields(path: Path) -> None:
    fields, _ = _read(path)
    assert set(fields) == ROLE_FIELDS, (
        f"{path}: frontmatter is {sorted(fields)}, expected exactly {sorted(ROLE_FIELDS)}"
    )
    assert fields["name"] == path.stem, f"{path}: name must equal the file's own name"


@pytest.mark.parametrize("path", ROLE_FILES, ids=lambda p: p.stem)
def test_a_role_names_the_phase_it_serves(path: Path) -> None:
    fields, _ = _read(path)
    assert fields["phase"] in PHASES, (
        f"{path}: phase is {fields['phase']!r}, expected one of {sorted(PHASES)}"
    )


# The persona section every role opens its body with (design D7 of `agent-teams`): the
# first `##` heading, one paragraph of at most this many lines, an emoji and a bold name.
PERSONA_HEADING = "## Who you are"
PERSONA_MAX_LINES = 5
_BOLD_NAME = re.compile(r"\*\*([^*\n]+)\*\*")


def _persona(body: str) -> tuple[str, list[str]]:
    """The first `##` heading of a body and the lines of the paragraph under it, up to
    the next `##` heading, blank lines dropped."""
    headings = [line for line in body.split("\n") if line.startswith("## ")]
    assert headings, "no `##` heading in the body"
    lines = body.split("\n")
    start = lines.index(headings[0]) + 1
    paragraph: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.strip():
            paragraph.append(line)
    return headings[0], paragraph


@pytest.mark.parametrize("path", ROLE_FILES, ids=lambda p: p.stem)
def test_a_role_opens_with_who_it_is(path: Path) -> None:
    """The opening paragraph under the title stays, and the first `##` section is the
    persona — so a reader meets the constraint before the name, never the other way."""
    _, body = _read(path)
    heading, _ = _persona(body)
    assert heading == PERSONA_HEADING, (
        f"{path}: the first `##` heading is {heading!r}, expected {PERSONA_HEADING!r}"
    )


@pytest.mark.parametrize("path", ROLE_FILES, ids=lambda p: p.stem)
def test_a_persona_is_one_short_paragraph(path: Path) -> None:
    """At most five physical lines and no blank line between them: a persona is read at
    every start, so it is bounded by shape rather than by taste."""
    _, body = _read(path)
    _, paragraph = _persona(body)
    assert paragraph, f"{path}: nothing under {PERSONA_HEADING!r}"
    assert len(paragraph) <= PERSONA_MAX_LINES, (
        f"{path}: the persona is {len(paragraph)} lines, at most {PERSONA_MAX_LINES} allowed"
    )
    lines = body.split("\n")
    first, last = lines.index(paragraph[0]), lines.index(paragraph[-1])
    assert all(line.strip() for line in lines[first : last + 1]), (
        f"{path}: the persona holds a blank line, so it is more than one paragraph"
    )


@pytest.mark.parametrize("path", ROLE_FILES, ids=lambda p: p.stem)
def test_a_persona_opens_with_the_emoji_the_description_opens_with(path: Path) -> None:
    """One code point of category `So` — no joiner or variation-selector sequence — and
    the same one at the head of `description`, since that is what a listing shows."""
    fields, body = _read(path)
    _, paragraph = _persona(body)
    emoji = paragraph[0][0]
    assert unicodedata.category(emoji) == "So", (
        f"{path}: the persona opens with {emoji!r}, which is not an emoji (category `So`)"
    )
    description = fields["description"]
    assert description[0] == emoji, (
        f"{path}: `description` opens with {description[0]!r}, but the persona with {emoji!r}"
    )
    assert description[1] == " " and description[2] != " ", (
        f"{path}: `description` needs exactly one space after its emoji"
    )
    assert paragraph[0][1] == " " and paragraph[0][2] != " ", (
        f"{path}: the persona needs exactly one space after its emoji"
    )


@pytest.mark.parametrize("path", ROLE_FILES, ids=lambda p: p.stem)
def test_a_persona_names_the_role_in_bold(path: Path) -> None:
    """A bold given name follows the emoji on the first line: the name is how a person
    refers to the role, so it is the one thing the section must make easy to find."""
    _, body = _read(path)
    _, paragraph = _persona(body)
    match = _BOLD_NAME.match(paragraph[0], 2)
    assert match, f"{path}: no `**Name**` after the emoji on {paragraph[0]!r}"
    assert match.group(1).strip(), f"{path}: the bold name is empty"


UNSURE_WORDS = ("not sure", "suspected", "unsure", "uncertain")

REVIEWING_PHASES = {"review", "verify"}

REVIEWING_ROLE_FILES = [p for p in ROLE_FILES if _read(p)[0].get("phase") in REVIEWING_PHASES]


@pytest.mark.parametrize("path", REVIEWING_ROLE_FILES, ids=lambda p: p.stem)
def test_a_reviewing_persona_says_when_it_is_unsure(path: Path) -> None:
    """A `review`- or `verify`-phase role lists saying when it is unsure among its
    traits, so the persona restates the uncertainty rule rather than competing with it.
    Only the words are checked here; whether the trait makes sense is the verifier's."""
    fields, body = _read(path)
    _, paragraph = _persona(body)
    text = " ".join(paragraph).lower()
    assert any(word in text for word in UNSURE_WORDS), (
        f"{path}: a {fields['phase']} role's persona says nothing about being unsure "
        f"(none of {UNSURE_WORDS} appears)"
    )


def test_no_two_roles_share_a_name_or_an_emoji() -> None:
    """The persona exists so that ten roles can be told apart in a listing and in
    `review`'s labelled output, which a repeated name or emoji would undo."""
    names: dict[str, Path] = {}
    emojis: dict[str, Path] = {}
    for path in ROLE_FILES:
        _, body = _read(path)
        _, paragraph = _persona(body)
        emoji = paragraph[0][0]
        name = _BOLD_NAME.match(paragraph[0], 2).group(1)
        assert emoji not in emojis, f"{path} and {emojis[emoji]} share the emoji {emoji!r}"
        assert name not in names, f"{path} and {names[name]} share the name {name!r}"
        emojis[emoji] = path
        names[name] = path


def test_there_is_at_least_one_skill() -> None:
    assert SKILL_FILES, "no skills under plugin/skills/"


def test_the_reviewer_is_explicitly_started_on_opus() -> None:
    review_skill = Path(__file__).resolve().parent.parent / "plugin" / "skills" / "review" / "SKILL.md"
    assert "model: opus" in review_skill.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", SKILL_FILES, ids=lambda p: p.parent.name)
def test_a_skill_has_exactly_the_minimum_frontmatter(path: Path) -> None:
    fields, _ = _read(path)
    assert set(fields) == SKILL_FIELDS, (
        f"{path}: frontmatter is {sorted(fields)}, expected exactly {sorted(SKILL_FIELDS)}"
    )
    assert fields["name"] == path.parent.name, f"{path}: name must equal the skill's directory name"
