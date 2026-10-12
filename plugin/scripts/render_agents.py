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

The plugin's own agents under ``agents/`` are the same rendering without a profile
(D8): ``sync`` rewrites every adapter already present there from the role of its name —
``name``, ``description``, ``tools``, no ``phase``, the body whole — so a role is edited
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

# A role file opens with exactly these four fields, in this order (design.md D2). The
# rendered agent keeps the first three and drops `phase`, which is the skills' concern.
ROLE_FIELDS = ("name", "description", "tools", "phase")
AGENT_FIELDS = ("name", "description", "tools")

# The four phases a role can belong to (design.md D2), and the two whose roles take a
# fragment. The other two write or bind a verdict, and a stack must not be able to put
# either behind a new name.
PHASES = ("apply", "propose", "review", "verify")
FRAGMENT_PHASES = frozenset({"review", "propose"})

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
    """One role as the harness holds it: its four fields and the prose an agent reads."""

    name: str
    description: str
    tools: str
    phase: str
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
    if not body.strip():
        raise AgentError(f"{path}: has no body")

    return Role(
        name=fields["name"],
        description=fields["description"],
        tools=fields["tools"],
        phase=fields["phase"],
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
    """The plugin's own agent for a role: the role without a profile and without `phase`.

    The body is copied whole, so the adapter carries the role's persona unchanged (D7)
    and a reader of either file reads the same prose.
    """
    return _compose(role.name, role.description, role.tools, role.body)


def render_agent(profile: str, role: Role, fragment: str) -> bytes:
    """One rendered agent: the role's three agent fields, its body whole, the fragment.

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


def _walk(
    profiles: list[str],
    plugin_root: Path | None,
    profiles_dir: Path | None,
) -> list[tuple[str, Role, bytes]]:
    """Every agent the chosen profiles call for, as (path, role, rendered bytes), sorted.

    The one place a fragment meets its role, so `render` and `agents_for` accept and
    refuse exactly the same teams. Profiles are read as a set, so the result depends on
    which were chosen and never on how they were listed. Nothing is returned until every
    fragment has been accepted: a refusal renders nothing.
    """
    root = plugin_root or default_plugin_root()
    source = profiles_dir or default_profiles_dir(root)
    walked: dict[str, tuple[Role, bytes]] = {}
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
            walked[agent_path(profile, specialist)] = (
                role,
                render_agent(profile, role, fragment.read_text(encoding="utf-8")),
            )
    return [(path, role, content) for path, (role, content) in sorted(walked.items())]


def render(
    profiles: list[str],
    plugin_root: Path | None = None,
    profiles_dir: Path | None = None,
) -> dict[str, bytes]:
    """Render every agent the chosen profiles call for, as `{path: bytes}` sorted by path."""
    return {path: content for path, _, content in _walk(profiles, plugin_root, profiles_dir)}


def agents_for(
    profiles: list[str],
    phase: str,
    plugin_root: Path | None = None,
    profiles_dir: Path | None = None,
) -> list[Agent]:
    """The agents the chosen profiles render for one phase, sorted by name.

    What a skill asks before fanning out (design.md D4): `review` for the reviewers to
    start, `propose` for the advisors to consult. The emoji is read back from the
    rendered agent's own `description`, not from the role, so it is by construction what
    the host shows for that agent (D7). Every refusal `render` makes, this makes too.
    """
    if phase not in PHASES:
        raise AgentError(f"no such phase: {phase}. The phases are {', '.join(PHASES)}.")
    agents: list[Agent] = []
    for path, role, content in _walk(profiles, plugin_root, profiles_dir):
        if role.phase != phase:
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
        "--profiles", required=True, type=_csv, help="the profiles chosen, comma separated"
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
            for agent in agents_for(args.profiles, args.phase, args.plugin_root):
                print(f"{agent.emoji} {agent.name}")
            return 0
        agents = render(args.profiles, args.plugin_root)
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
