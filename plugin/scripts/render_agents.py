#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Render a project's stack agents from the profiles it chose.

Pillar 3's renderer. A profile directory is a team (design.md D1): ``profile.md`` is the
stack, and every ``<specialist>.md`` beside it is that stack's addition to the role of the
same name. For each such fragment this script joins the role's frontmatter and body with
the fragment under a heading naming the profile (D2), and returns ``{path: bytes}`` for
``setup`` to place under ``.claude/agents/`` and own by hash (D3). The output is a pure
function of the chosen profiles and the harness's own content: no timestamp, no version,
no dependence on the order the profiles were given.

    uv run plugin/scripts/render_agents.py render --profiles alpha,beta
    uv run plugin/scripts/render_agents.py render --profiles alpha --out-dir .

A fragment that names no role is refused, not skipped, so a typo in a file name cannot
silently drop a specialist. A fragment for an ``apply``- or ``verify``-phase role is
refused too: only ``review``- and ``propose``-phase roles take one, which is what keeps
every rendered agent read-only.

The skills that start those agents ask the same code which ones a project should have
in a given phase (D2, D4): ``list`` prints one line per agent, the first code point of
its rendered ``description`` — the role's emoji (D7) — a space, and its ``name``, so a
skill labels a review without ever parsing an agent's body.

    uv run plugin/scripts/render_agents.py list --profiles alpha,beta --phase review

Both commands take a roster as ``--team`` and ``--bench`` (design.md D5 of
`agent-roster`): comma separated, given together or not at all, an empty value a present
empty list. With one, ``--profiles`` may be empty, and a roster name no profile holds a
fragment for is its generic agent; a bench agent is rendered and never listed.

    uv run plugin/scripts/render_agents.py list --profiles "" --team x --bench "" --phase review

The plugin's own agents under ``agents/`` are the same rendering without a profile
(D8): ``sync`` rewrites every adapter already present there from the role of its name —
``name``, ``description``, ``tools``, no ``phase`` or ``department``, the body whole — so a role is edited
once and its adapter regenerated, never maintained. ``--check`` writes nothing and names
each adapter that differs, which is what the correspondence test asserts is empty. An
adapter whose role does not exist is refused by name; the set of core agents is the set
of files in that directory, and nothing else lists them.

    uv run plugin/scripts/render_agents.py sync
    uv run plugin/scripts/render_agents.py sync --check

No dependency outside the standard library, deliberately: setup calls this code, and a
project's first contact with the harness should not begin by resolving one.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# A role file opens with exactly these five fields, in this order (design.md D2, and D4
# of `agent-roster`). The rendered agent keeps the first three and drops `phase`, which is
# the skills' concern, and `department`, which groups roles and gates nothing.
ROLE_FIELDS = ("name", "description", "tools", "phase", "department")
AGENT_FIELDS = ("name", "description", "tools")

# The four phases a role can belong to (design.md D2), and the two whose roles take a
# fragment. The other two write or bind a verdict, and a stack must not be able to put
# either behind a new name.
PHASES = ("apply", "propose", "review", "verify")
FRAGMENT_PHASES = frozenset({"review", "propose"})

# The departments a role can belong to (design.md D4 of `agent-roster`). A role declares
# exactly one; anything else is refused by name.
DEPARTMENTS = ("engineering", "design")

PROFILE_FILE = "profile.md"
AGENTS_DIR = ".claude/agents"
PLUGIN_AGENTS_DIR = "agents"
STACK_HEADING = "## For this stack: {profile}"

_DELIMITER = "---"
_FIELD = re.compile(r"^([a-z][a-z_]*): *(\S.*?) *$")


class AgentError(ValueError):
    """A role, a profile or a request to render one that cannot be honoured."""


@dataclass(frozen=True)
class Role:
    """One role as the harness holds it: its five fields and the prose an agent reads."""

    name: str
    description: str
    tools: str
    phase: str
    department: str
    body: str
    path: Path


@dataclass(frozen=True)
class Agent:
    """One agent a project should have: what a skill needs to start it and label it."""

    name: str
    emoji: str
    path: str
    role: str
    phase: str


def default_plugin_root() -> Path:
    """The plugin root relative to this script, installed or in a checkout."""
    return Path(__file__).resolve().parent.parent


def roles_dir(plugin_root: Path) -> Path:
    return plugin_root / "orchestration" / "roles"


def agents_dir(plugin_root: Path) -> Path:
    """Where the plugin's own adapters live: the host reads them at the plugin root."""
    return plugin_root / PLUGIN_AGENTS_DIR


def default_profiles_dir(plugin_root: Path) -> Path:
    return plugin_root / "tools" / "profiles"


def parse_frontmatter(text: str, path: Path) -> tuple[dict[str, str], str]:
    """Split a role file into its fields and its body.

    The format is `key: value` scalars and nothing else, the same shape the rules use.
    Anything else is refused rather than guessed at.
    """
    lines = text.split("\n")
    if not lines or lines[0].rstrip() != _DELIMITER:
        raise AgentError(f"{path}: does not open with a `{_DELIMITER}` frontmatter block")
    try:
        end = lines.index(_DELIMITER, 1)
    except ValueError:
        raise AgentError(f"{path}: the frontmatter block is never closed") from None

    fields: dict[str, str] = {}
    for offset, line in enumerate(lines[1:end], start=2):
        match = _FIELD.match(line)
        if not match:
            raise AgentError(
                f"{path}:{offset}: {line!r} is not `key: value`. Role frontmatter holds "
                f"{', '.join(ROLE_FIELDS)} as plain strings; nothing else is read."
            )
        key, value = match.group(1), match.group(2)
        if key in fields:
            raise AgentError(f"{path}:{offset}: `{key}` is declared twice")
        fields[key] = value
    return fields, "\n".join(lines[end + 1 :])


def read_role(path: Path) -> Role:
    """Read one role file, refusing anything the renderer could not render faithfully."""
    if not path.is_file():
        raise AgentError(f"{path}: no such role")
    fields, body = parse_frontmatter(path.read_text(encoding="utf-8"), path)

    missing = [field for field in ROLE_FIELDS if field not in fields]
    if missing:
        raise AgentError(f"{path}: declares no {', '.join(missing)}")
    unknown = sorted(set(fields) - set(ROLE_FIELDS))
    if unknown:
        raise AgentError(
            f"{path}: declares {', '.join(unknown)}, which a role does not hold. The "
            f"fields are {', '.join(ROLE_FIELDS)}."
        )
    if fields["name"] != path.stem:
        raise AgentError(
            f"{path}: declares name `{fields['name']}` but is named `{path.stem}`"
        )
    if fields["department"] not in DEPARTMENTS:
        raise AgentError(
            f"{path}: declares department `{fields['department']}`, which is none of "
            f"{', '.join(DEPARTMENTS)}"
        )
    if not body.strip():
        raise AgentError(f"{path}: has no body")

    return Role(
        name=fields["name"],
        description=fields["description"],
        tools=fields["tools"],
        phase=fields["phase"],
        department=fields["department"],
        body=body,
        path=path,
    )


def phase_of(role: Role) -> str:
    """The phase a role belongs to, refused unless it is one of the four."""
    if role.phase not in PHASES:
        raise AgentError(
            f"{role.path}: declares phase `{role.phase}`, which is none of "
            f"{', '.join(PHASES)}"
        )
    return role.phase


def held_roles(plugin_root: Path) -> list[str]:
    """The roles the harness holds, by file name, sorted."""
    directory = roles_dir(plugin_root)
    if not directory.is_dir():
        raise AgentError(f"{directory} is not a directory of roles")
    return sorted(path.stem for path in directory.glob("*.md"))


def held_specialists(plugin_root: Path) -> list[dict[str, str]]:
    """The specialists a roster can name, sorted by department then name.

    A specialist is a role whose phase is `review` or `propose` and that does not ship as
    a plugin agent (design.md D2 of `agent-roster`). Which roles ship is read from the
    files under `agents/`, as `sync` reads it, so no list of core names lives here. The
    emoji is the first code point of the role's `description`, as `agents_for` reads it.
    """
    shipped = {path.stem for path in agents_dir(plugin_root).glob("*.md")}
    specialists: list[dict[str, str]] = []
    for name in held_roles(plugin_root):
        if name in shipped:
            continue
        role = read_role(roles_dir(plugin_root) / f"{name}.md")
        if phase_of(role) not in FRAGMENT_PHASES:
            continue
        specialists.append(
            {
                "specialist": role.name,
                "department": role.department,
                "emoji": role.description[0],
                "phase": role.phase,
            }
        )
    return sorted(specialists, key=lambda entry: (entry["department"], entry["specialist"]))


def fragments_of(profile: str, profiles_dir: Path) -> dict[str, Path]:
    """The fragments a profile carries, specialist by specialist.

    A profile directory's fragments are every `*.md` in it other than `profile.md`; a
    single-file profile carries none. A name that is neither is refused.
    """
    directory = profiles_dir / profile
    if directory.is_dir():
        if not (directory / PROFILE_FILE).is_file():
            raise AgentError(f"{directory}: a profile directory holds `{PROFILE_FILE}`")
        return {
            path.stem: path
            for path in sorted(directory.glob("*.md"))
            if path.name != PROFILE_FILE
        }
    if (profiles_dir / f"{profile}.md").is_file():
        return {}
    raise AgentError(f"no such profile: {profile}. " + _holdings(profiles_dir))


def _holdings(profiles_dir: Path) -> str:
    if not profiles_dir.is_dir():
        return f"{profiles_dir} is not a directory of profiles."
    held = sorted(
        path.name if path.is_dir() else path.stem
        for path in profiles_dir.iterdir()
        if path.is_dir() or path.suffix == ".md"
    )
    return f"The profiles held are: {', '.join(held)}."


def agent_path(profile: str, specialist: str) -> str:
    """Where the host reads a project agent, relative to the project root."""
    return f"{AGENTS_DIR}/{profile}-{specialist}.md"


def _compose(name: str, description: str, tools: str, body: str) -> bytes:
    """An agent file: the three agent fields, then the body, ending in one newline.

    The one place an agent's bytes are assembled, so a project's stack agent and the
    plugin's own adapter are the same rendering (design.md D8) and cannot drift apart.
    """
    frontmatter = "\n".join(
        [
            _DELIMITER,
            f"name: {name}",
            f"description: {description}",
            f"tools: {tools}",
            _DELIMITER,
        ]
    )
    return (frontmatter + "\n" + body.rstrip() + "\n").encode("utf-8")


def adapter_of(role: Role) -> bytes:
    """The plugin's own agent for a role: the role without a profile, `phase` or
    `department`.

    The body is copied whole, so the adapter carries the role's persona unchanged (D7)
    and a reader of either file reads the same prose.
    """
    return _compose(role.name, role.description, role.tools, role.body)


def render_agent(profile: str, role: Role, fragment: str) -> bytes:
    """One rendered agent: the role's three agent fields, its body whole, the fragment.

    `phase` and `department` are dropped, as for the plugin's own adapters.

    The body is copied as it stands so the role's persona reaches every stack agent
    unchanged (design.md D7); the fragment follows under a heading naming the profile.
    """
    stack = "\n" + STACK_HEADING.format(profile=profile) + "\n\n" + fragment.strip() + "\n"
    return _compose(
        f"{profile}-{role.name}",
        f"{role.description} — stack: {profile}",
        role.tools,
        role.body.rstrip() + "\n" + stack,
    )


def render_generic(role: Role) -> bytes:
    """The generic agent of a roster name no chosen profile holds a fragment for: the
    role's adapter, the same bytes `sync` writes under `agents/`, placed in the project
    at `.claude/agents/<name>.md` (design.md D3 of `agent-roster`). No stack heading, no
    description suffix."""
    return adapter_of(role)


def generic_path(specialist: str) -> str:
    """Where the host reads a project's generic agent, relative to the project root."""
    return f"{AGENTS_DIR}/{specialist}.md"


def _shipped(plugin_root: Path) -> set[str]:
    """The roles that ship as plugin agents, read from `agents/` as `sync` reads them."""
    return {path.stem for path in agents_dir(plugin_root).glob("*.md")}


def roster_refusal(entry: str, reason: str, specialists: list[dict[str, str]]) -> str:
    """The one wording of a roster refusal (design.md D2 of `agent-roster`): the entry,
    why it cannot be on a roster, and the specialists the harness holds.

    `specialists` is what `held_specialists()` returns. The renderer and setup's
    `validate_answers` both word their refusal here, so a roster is refused with the same
    text whichever path it reaches the harness by.
    """
    held = ", ".join(entry["specialist"] for entry in specialists) or "none"
    return f"`{entry}` cannot be on a roster: {reason}. The specialists held are: {held}."


def _roster_reason(name: str, plugin_root: Path) -> str | None:
    """Why a name cannot be on a roster, or None when it is a specialist the harness
    holds. The reasons are checked in the order a reader would ask them."""
    role_path = roles_dir(plugin_root) / f"{name}.md"
    if not role_path.is_file():
        return "it names no role the harness holds"
    role = read_role(role_path)
    if phase_of(role) not in FRAGMENT_PHASES:
        return (
            f"its phase is `{role.phase}`, and only a review- or propose-phase role can be "
            f"on a roster"
        )
    if name in _shipped(plugin_root):
        return "it ships as a plugin agent, so every project has it already"
    return None


def _check_roster(team: list[str], bench: list[str], plugin_root: Path) -> None:
    """Refuse a roster that names anything but a specialist held, or a name twice over."""
    specialists = held_specialists(plugin_root)
    for name in sorted(set(team) | set(bench)):
        reason = _roster_reason(name, plugin_root)
        if reason is not None:
            raise AgentError(roster_refusal(name, reason, specialists))
    for name in sorted(set(team) & set(bench)):
        raise AgentError(
            roster_refusal(name, "it is named on both the team and the bench", specialists)
        )


def _walk(
    profiles: list[str],
    plugin_root: Path | None,
    profiles_dir: Path | None,
    team: list[str] | None = None,
    bench: list[str] | None = None,
) -> list[tuple[str, Role, bytes]]:
    """Every agent the chosen profiles and roster call for, as (path, role, rendered
    bytes), sorted.

    The one place a fragment meets its role, so `render` and `agents_for` accept and
    refuse exactly the same teams. Profiles and roster names are read as sets, so the
    result depends on which were chosen and never on how they were listed. Nothing is
    returned until every fragment has been accepted: a refusal renders nothing.

    Without a roster (`team` and `bench` both None) every fragment of every chosen
    profile renders, and nothing else. With one (both given), each roster name renders
    one prefixed agent per chosen profile holding a fragment for it, or, when none does,
    its generic agent (design.md D2, D3 of `agent-roster`); a fragment for a name off the
    roster renders nothing, but is still checked like any other.
    """
    if (team is None) != (bench is None):
        raise AgentError(
            "a roster is `team` and `bench` together: "
            + ("`bench` is missing" if bench is None else "`team` is missing")
        )
    root = plugin_root or default_plugin_root()
    source = profiles_dir or default_profiles_dir(root)
    roster: set[str] | None = None
    if team is not None and bench is not None:
        _check_roster(team, bench, root)
        roster = set(team) | set(bench)
    shipped = _shipped(root)
    walked: dict[str, tuple[Role, bytes]] = {}
    covered: set[str] = set()
    for profile in sorted(set(profiles)):
        for specialist, fragment in fragments_of(profile, source).items():
            role_path = roles_dir(root) / f"{specialist}.md"
            if not role_path.is_file():
                raise AgentError(
                    f"{fragment}: names no role the harness holds. The roles held are: "
                    f"{', '.join(held_roles(root))}."
                )
            role = read_role(role_path)
            if phase_of(role) not in FRAGMENT_PHASES:
                raise AgentError(
                    f"{fragment}: `{role.name}` is a {role.phase}-phase role, and only a "
                    f"review- or propose-phase role takes a fragment."
                )
            if specialist in shipped:
                raise AgentError(
                    f"{fragment}: `{role.name}` ships as a plugin agent, so every project "
                    f"has it already, and a role that ships takes no fragment."
                )
            if roster is not None and specialist not in roster:
                continue
            covered.add(specialist)
            walked[agent_path(profile, specialist)] = (
                role,
                render_agent(profile, role, fragment.read_text(encoding="utf-8")),
            )
    for specialist in sorted((roster or set()) - covered):
        role = read_role(roles_dir(root) / f"{specialist}.md")
        walked[generic_path(specialist)] = (role, render_generic(role))
    return [(path, role, content) for path, (role, content) in sorted(walked.items())]


def render(
    profiles: list[str],
    plugin_root: Path | None = None,
    profiles_dir: Path | None = None,
    *,
    team: list[str] | None = None,
    bench: list[str] | None = None,
) -> dict[str, bytes]:
    """Render every agent the chosen profiles and roster call for, as `{path: bytes}`
    sorted by path. `team` and `bench` are given together or not at all."""
    return {
        path: content
        for path, _, content in _walk(profiles, plugin_root, profiles_dir, team, bench)
    }


def agents_for(
    profiles: list[str],
    phase: str,
    plugin_root: Path | None = None,
    profiles_dir: Path | None = None,
    *,
    team: list[str] | None = None,
    bench: list[str] | None = None,
) -> list[Agent]:
    """The agents the chosen profiles render for one phase, sorted by name.

    What a skill asks before fanning out (design.md D4): `review` for the reviewers to
    start, `propose` for the advisors to consult. The emoji is read back from the
    rendered agent's own `description`, not from the role, so it is by construction what
    the host shows for that agent (D7). Every refusal `render` makes, this makes too.
    With a roster, only the agents of team names are kept: a bench agent is rendered and
    never started.
    """
    if phase not in PHASES:
        raise AgentError(f"no such phase: {phase}. The phases are {', '.join(PHASES)}.")
    agents: list[Agent] = []
    for path, role, content in _walk(profiles, plugin_root, profiles_dir, team, bench):
        if role.phase != phase:
            continue
        if team is not None and role.name not in team:
            continue
        fields, _ = parse_frontmatter(content.decode("utf-8"), Path(path))
        agents.append(
            Agent(
                name=fields["name"],
                emoji=fields["description"][0],
                path=path,
                role=role.name,
                phase=role.phase,
            )
        )
    return sorted(agents, key=lambda agent: agent.name)


def sync(plugin_root: Path | None = None, check: bool = False) -> list[str]:
    """Bring every adapter under `agents/` to the rendering of its role; name the stale.

    The set of adapters is the `*.md` files already present there (design.md D8): a new
    core agent is an empty file of the role's name, filled by the next run, and no list
    in this script says which roles are core. An adapter whose role does not exist is
    refused by name, and nothing is written until every adapter has been accepted. With
    `check`, nothing is written at all; the names returned are the adapters that differ
    — and, without `check`, that were just rewritten. Running it twice changes nothing
    the second time.
    """
    root = plugin_root or default_plugin_root()
    directory = agents_dir(root)
    if not directory.is_dir():
        raise AgentError(f"{directory} is not a directory of agents")
    rendered: dict[Path, bytes] = {}
    for adapter in sorted(directory.glob("*.md")):
        role_path = roles_dir(root) / adapter.name
        if not role_path.is_file():
            raise AgentError(
                f"{adapter}: binds no role the harness holds. The roles held are: "
                f"{', '.join(held_roles(root))}."
            )
        rendered[adapter] = adapter_of(read_role(role_path))
    stale = [
        adapter for adapter, content in rendered.items() if adapter.read_bytes() != content
    ]
    if not check:
        for adapter in stale:
            adapter.write_bytes(rendered[adapter])
    return [adapter.stem for adapter in stale]


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parser() -> argparse.ArgumentParser:
    located = argparse.ArgumentParser(add_help=False)
    located.add_argument(
        "--plugin-root",
        type=Path,
        default=None,
        help="read roles and profiles from this plugin instead of the one this script is in",
    )
    common = argparse.ArgumentParser(add_help=False, parents=[located])
    common.add_argument(
        "--profiles",
        required=True,
        type=_csv,
        help="the profiles chosen, comma separated; empty for a roster with no profile",
    )
    common.add_argument(
        "--team",
        type=_csv,
        default=None,
        help="the roster's team, comma separated; given with --bench, empty for none",
    )
    common.add_argument(
        "--bench",
        type=_csv,
        default=None,
        help="the roster's bench, comma separated; given with --team, empty for none",
    )

    parser = argparse.ArgumentParser(
        description="Render a project's stack agents from the profiles it chose, "
        "list the ones a phase starts, or sync the plugin's own agents with their roles.",
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="command")

    render_command = commands.add_parser(
        "render",
        parents=[common],
        help="render the agents; list their paths, or write them under --out-dir",
        description="Render every agent the chosen profiles call for.",
    )
    render_command.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="a project root to write the agents under; without it, the paths are listed",
    )

    list_command = commands.add_parser(
        "list",
        parents=[common],
        help="print `<emoji> <name>` for each agent of one phase",
        description="Print, one per line, `<emoji> <name>` for every agent the chosen "
        "profiles render whose role belongs to the phase. Nothing is printed for a "
        "project with no such agent.",
    )
    list_command.add_argument(
        "--phase", required=True, choices=PHASES, help="the phase whose agents to list"
    )

    sync_command = commands.add_parser(
        "sync",
        parents=[located],
        help="rewrite each plugin agent from its role, or with --check only name the stale",
        description="Rewrite every adapter present under the plugin's `agents/` from the "
        "role of the same name, printing `synced <name>` for each one that changed. "
        "With --check nothing is written: `stale <name>` is printed for each adapter "
        "that differs, and the exit status is 1 if there is any.",
    )
    sync_command.add_argument(
        "--check",
        action="store_true",
        help="write nothing; name each stale adapter and exit 1 if there is one",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        if args.command == "sync":
            stale = sync(args.plugin_root, check=args.check)
            for name in stale:
                print(f"{'stale' if args.check else 'synced'} {name}")
            return 1 if args.check and stale else 0
        if args.command == "list":
            for agent in agents_for(
                args.profiles, args.phase, args.plugin_root, team=args.team, bench=args.bench
            ):
                print(f"{agent.emoji} {agent.name}")
            return 0
        agents = render(args.profiles, args.plugin_root, team=args.team, bench=args.bench)
    except AgentError as error:
        print(f"render_agents: {error}", file=sys.stderr)
        return 2

    for relative, content in agents.items():
        if args.out_dir is None:
            print(relative)
            continue
        destination = args.out_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
