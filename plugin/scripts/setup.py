#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Bring a project to a harnessed state, or say why it cannot be brought there.

Pillar 2's setup script. It surveys every path it could touch, plans what it would do to
each one, refuses to write while any conflict stands, and then writes each file
atomically with the record last.

The questions belong to the session that can explain them, so this script never prompts:
it takes the answers, and the approvals the person gave, as one document.

    uv run plugin/scripts/setup.py plan  --answers answers.json --project .
    uv run plugin/scripts/setup.py write --answers answers.json --project .

No dependency outside the standard library: a project's first contact with the harness
should not begin by resolving one.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_rules  # noqa: E402  (a sibling script, reached the way the host reaches it)

# --- what a harnessed project holds -------------------------------------------------

AGENTS = "AGENTS.md"
CLAUDE = "CLAUDE.md"
CHOICES = ".harnex.yml"
OPENSPEC_CONFIG = "openspec/config.yaml"
RULES = ".harnex/rules.md"
STATE_IGNORE = ".harnex/state/.gitignore"
MANIFEST = ".harnex/manifest.json"
SETTINGS = ".claude/settings.json"
MCP_CONFIG = ".mcp.json"
ENV_FILE = ".env"

# Local visibility (docs/PLAN.md C7): nothing below is created, read or merged unless
# `answers.visibility == "local"`. Shared visibility above is untouched by any of it.
CLAUDE_LOCAL = "CLAUDE.local.md"
LOCAL_CHOICES = ".harnex/config.yml"
HARNEX_IGNORE = ".harnex/.gitignore"
GIT_EXCLUDE = ".git/info/exclude"
SETTINGS_LOCAL = ".claude/settings.local.json"
GLOBAL_SETTINGS = ".claude/settings.json"  # resolved against `home`, not `project`

PROJECT_PATHS = (AGENTS, CLAUDE, CHOICES, OPENSPEC_CONFIG)
HARNESS_PATHS = (RULES, STATE_IGNORE)
LOCAL_HARNESS_PATHS = (RULES, HARNEX_IGNORE, CLAUDE_LOCAL)

# The answers, in the order they are written. The names are fixed by the plan.
ANSWER_KEYS = (
    "project_name",
    "profiles",
    "sets",
    "features",
    "canary",
    "decision_model",
    "check_command",
)
# `.harnex/config.yml`'s own shape, local visibility only (design.md D2): the same seven
# plus the three local-visibility answers. A new file, not a rename of `.harnex.yml` —
# `.harnex.yml`'s own shape (above) is not reopened.
LOCAL_ANSWER_KEYS = ANSWER_KEYS + ("visibility", "tools", "store_id")
LIST_KEYS = ("profiles", "sets", "features")
LOCAL_LIST_KEYS = LIST_KEYS + ("tools",)
DECISION_BACKENDS = ("mock", "jev")
VISIBILITIES = ("shared", "local")
# The builder role's own two bindings (docs/PLAN.md §4) — the only role with a choice of
# tool, so the only one local visibility's guided question asks about by name.
BUILDER_TOOLS = ("claude", "codex")

STATE_IGNORE_BODY = """\
# Runtime state the harness writes while it works: decision journal, apply run state.
# It ignores itself so that the project's own ignore file is never touched.
*
"""

HARNEX_IGNORE_BODY = """\
# Local visibility (docs/PLAN.md C7): everything in this directory is personal to this
# machine — your answers, the rendered rules, the generation record, runtime state. It
# ignores itself, the same way `.harnex/state/` already does under shared visibility, so
# that the project's own ignore file is never touched.
*
"""

CLAUDE_LOCAL_BODY_MARKER = "@.harnex/rules.md"

CODEX_LOCAL_NOTICE = (
    "Codex is among the active tools, but under local visibility it cannot see this "
    "project's rules: the Codex builder binding reads them from `AGENTS.md`, which "
    "local visibility never touches. Codex is not blocked — it will still build — it "
    "simply will not have read the rules first."
)

MANIFEST_FORMAT = 1
FLOOR_FORMAT = 1

BYPASS_MODES = ("bypassPermissions",)

PLAYWRIGHT_MCP = {"command": "npx", "args": ["@playwright/mcp@latest"]}

# What setup proposes when a project chooses the canary set. The word itself is the
# project's to change; the proposal lives here so that no command has to remember it.
DEFAULT_CANARY = "Hullaballoo!"


def canary_block(answers: "Answers") -> str:
    """The paragraph `AGENTS.md` states the word in, or nothing if the set is not chosen.

    `.harnex/rules.md` states the rule but never the word: it is a pure function of the
    chosen sets, so a project fact does not belong in it. The word is the project's own,
    so it belongs in `AGENTS.md` instead — the one place an agent actually reads it from.
    """
    if "canary" not in answers.sets:
        return ""
    return (
        "## Canary\n\n"
        f"End every answer with the word `{answers.canary}`. The harness's `Stop` hook\n"
        "reads it and warns — never blocks — when it is missing, which is the cheapest\n"
        "sign these instructions have dropped out of context.\n\n"
    )


class SetupError(Exception):
    """Something the harness will not guess at: it stops and says what it found."""


# --- the project's answers ----------------------------------------------------------


@dataclass(frozen=True)
class Answers:
    project_name: str
    profiles: tuple[str, ...]
    sets: tuple[str, ...]
    features: tuple[str, ...]
    canary: str
    decision_model: str
    check_command: str
    pointer_agents: bool = False
    pointer_claude: bool = False
    mcp_playwright: bool = False
    adopt: tuple[str, ...] = ()
    # Local visibility (docs/PLAN.md C7). `visibility`/`tools`/`store_id` are answers,
    # like the seven above, but recorded in `.harnex/config.yml`, never in `.harnex.yml`
    # (design.md D2) — so they are not in `as_choices()`. `global_instructions` is an
    # approval, like `pointer_agents`, not a recorded answer at all.
    visibility: str = "shared"
    tools: tuple[str, ...] = ()
    store_id: str = ""
    global_instructions: bool = False

    def as_choices(self) -> dict[str, object]:
        """Only the seven `.harnex.yml` records; the approvals are this run's, not the
        project's, and local visibility's own answers belong to `.harnex/config.yml`
        instead (`as_local_choices`)."""
        return {
            "project_name": self.project_name,
            "profiles": list(self.profiles),
            "sets": list(self.sets),
            "features": list(self.features),
            "canary": self.canary,
            "decision_model": self.decision_model,
            "check_command": self.check_command,
        }

    def as_local_choices(self) -> dict[str, object]:
        """The ten `.harnex/config.yml` records: the same seven, plus local visibility's
        own three."""
        choices = self.as_choices()
        choices["visibility"] = self.visibility
        choices["tools"] = list(self.tools)
        choices["store_id"] = self.store_id
        return choices


def available_sets(plugin_root: Path) -> list[str]:
    return render_rules.available_sets(plugin_root / "context" / "rules")


def available_profiles(plugin_root: Path) -> list[str]:
    """The profiles the harness holds, declared as files or profile directories."""
    directory = plugin_root / "tools" / "profiles"
    if not directory.is_dir():
        return []
    return sorted(
        path.name if path.is_dir() else path.stem
        for path in directory.iterdir()
        if path.is_dir() or path.suffix == ".md"
    )


def available_features(plugin_root: Path) -> list[str]:
    """The features the harness holds, declared in one file. Absent until the first."""
    registry = plugin_root / "tools" / "features.json"
    if not registry.is_file():
        return []
    try:
        declared = json.loads(registry.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SetupError(f"{registry}: {error}") from error
    return sorted(str(item["name"]) for item in declared)


def ui_profiles(plugin_root: Path) -> list[str]:
    """The profiles that declare a UI stack, from the profile-owned registry."""
    registry = plugin_root / "tools" / "profiles" / "ui.json"
    if not registry.is_file():
        return []
    try:
        declared = json.loads(registry.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SetupError(f"{registry}: {error}") from error
    return sorted(str(item) for item in declared)


def read_answers(text: str, plugin_root: Path) -> Answers:
    """Read the answers document and refuse anything the harness cannot honour."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise SetupError(f"the answers are not readable as JSON: {error}") from error
    if not isinstance(raw, dict):
        raise SetupError("the answers must be an object with the project's choices")

    approvals = raw.get("approvals", {})
    if not isinstance(approvals, dict):
        raise SetupError("`approvals` must be an object")
    local_keys = {"visibility", "tools", "store_id"}
    unknown_keys = sorted(set(raw) - set(ANSWER_KEYS) - local_keys - {"approvals"})
    if unknown_keys:
        raise SetupError(
            f"the answers name what the harness does not ask for: {', '.join(unknown_keys)}"
        )

    values: dict[str, object] = {}
    for key in ANSWER_KEYS:
        if key in LIST_KEYS:
            value = raw.get(key, [])
            if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
                raise SetupError(f"`{key}` must be a list of names")
            values[key] = tuple(value)
        else:
            value = raw.get(key, "")
            if not isinstance(value, str):
                raise SetupError(f"`{key}` must be text")
            values[key] = value

    visibility = raw.get("visibility", "shared")
    if not isinstance(visibility, str):
        raise SetupError("`visibility` must be text")
    tools_raw = raw.get("tools", [])
    if not isinstance(tools_raw, list) or any(not isinstance(v, str) for v in tools_raw):
        raise SetupError("`tools` must be a list of names")
    store_id = raw.get("store_id", "")
    if not isinstance(store_id, str):
        raise SetupError("`store_id` must be text")

    answers = Answers(
        project_name=str(values["project_name"]),
        profiles=tuple(values["profiles"]),  # type: ignore[arg-type]
        sets=tuple(values["sets"]),  # type: ignore[arg-type]
        features=tuple(values["features"]),  # type: ignore[arg-type]
        canary=str(values["canary"]),
        decision_model=str(values["decision_model"]),
        check_command=str(values["check_command"]),
        pointer_agents=bool(approvals.get("pointer_agents", False)),
        pointer_claude=bool(approvals.get("pointer_claude", False)),
        mcp_playwright=bool(approvals.get("mcp_playwright", False)),
        adopt=tuple(approvals.get("adopt", ()) or ()),
        visibility=visibility,
        tools=tuple(tools_raw),
        store_id=store_id,
        global_instructions=bool(approvals.get("global_instructions", False)),
    )
    validate_answers(answers, plugin_root)
    return answers


def validate_answers(answers: Answers, plugin_root: Path) -> None:
    if not answers.project_name.strip():
        raise SetupError("`project_name` is the one answer with no default")
    if not answers.check_command.strip():
        raise SetupError(
            "`check_command` is the command that must pass before anything is called done"
        )
    if answers.decision_model not in DECISION_BACKENDS:
        raise SetupError(
            f"`decision_model` is `{answers.decision_model}`; the backends are "
            f"{', '.join(DECISION_BACKENDS)}"
        )

    held = {
        "sets": available_sets(plugin_root),
        "profiles": available_profiles(plugin_root),
        "features": available_features(plugin_root),
    }
    for key in LIST_KEYS:
        chosen = getattr(answers, key)
        unknown = sorted(set(chosen) - set(held[key]))
        if unknown:
            holds = ", ".join(held[key]) if held[key] else "none"
            raise SetupError(
                f"no such {key[:-1]}: {', '.join(unknown)}. The harness holds: {holds}."
            )
    if not answers.sets:
        raise SetupError(
            "no rule set was chosen. The harness holds: " + ", ".join(held["sets"]) + "."
        )
    if "canary" in answers.sets and not answers.canary.strip():
        raise SetupError("the `canary` set is chosen, so the project needs a canary word")
    if "canary" not in answers.sets and answers.canary.strip():
        raise SetupError(
            "a canary word is recorded but the `canary` set was not chosen; "
            "the word would be read by nothing"
        )
    if answers.visibility not in VISIBILITIES:
        raise SetupError(
            f"`visibility` is `{answers.visibility}`; it must be one of "
            f"{', '.join(VISIBILITIES)}"
        )
    unknown_tools = sorted(set(answers.tools) - set(BUILDER_TOOLS))
    if unknown_tools:
        raise SetupError(
            f"no such tool: {', '.join(unknown_tools)}. The harness holds: "
            f"{', '.join(BUILDER_TOOLS)}."
        )
    if answers.tools and answers.visibility != "local":
        raise SetupError(
            "`tools` is answered but `visibility` is not `local`; it would be read by "
            "nothing"
        )
    if answers.visibility == "local" and not answers.store_id.strip():
        raise SetupError(
            "`visibility` is `local`, so a local OpenSpec store must already be "
            "resolved — register one with `openspec store setup` and pass its id as "
            "`store_id` before planning or writing"
        )
    if answers.visibility != "local" and answers.store_id.strip():
        raise SetupError(
            "`store_id` is answered but `visibility` is not `local`; it would be read "
            "by nothing"
        )
    for path in answers.adopt:
        if path not in HARNESS_PATHS and path not in LOCAL_HARNESS_PATHS:
            raise SetupError(f"{path} is not a path the harness owns, so it cannot adopt it")


def choices_on_offer(plugin_root: Path) -> dict[str, object]:
    """What a project may choose, derived from what the harness holds, not from a list."""
    return {
        "sets": available_sets(plugin_root),
        "profiles": available_profiles(plugin_root),
        "features": available_features(plugin_root),
        "decision_models": list(DECISION_BACKENDS),
        "default_canary": DEFAULT_CANARY,
        "visibilities": list(VISIBILITIES),
        "tools": list(BUILDER_TOOLS),
    }


# --- the project's choices file, written and read as one flat shape -----------------

_SCALAR = re.compile(r"^([a-z][a-z_]*): +(\S.*?)\s*$")
_LIST_HEAD = re.compile(r"^([a-z][a-z_]*):\s*$")
_LIST_ITEM = re.compile(r"^ +- +(\S.*?)\s*$")


def parse_choices(
    text: str,
    path: str = CHOICES,
    keys: tuple[str, ...] = ANSWER_KEYS,
    list_keys: tuple[str, ...] = LIST_KEYS,
) -> dict[str, object]:
    """The reader is the schema: what it does not understand, it refuses, with the line.

    `keys`/`list_keys` default to `.harnex.yml`'s own shape; `.harnex/config.yml` (local
    visibility, design.md D2) passes `LOCAL_ANSWER_KEYS`/`LOCAL_LIST_KEYS` instead — the
    line-level grammar is the same flat shape either way.
    """
    values: dict[str, object] = {}
    current: str | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = _LIST_ITEM.match(line)
        if item:
            if current is None:
                raise SetupError(f"{path}:{number}: a list item before any key")
            values[current].append(_unquote(item.group(1)))  # type: ignore[union-attr]
            continue
        scalar = _SCALAR.match(line)
        if scalar:
            key, value = scalar.group(1), _unquote(scalar.group(2))
            _claim(values, key, path, number)
            values[key] = value
            current = None
            continue
        head = _LIST_HEAD.match(line)
        if head:
            key = head.group(1)
            _claim(values, key, path, number)
            values[key] = []
            current = key
            continue
        raise SetupError(
            f"{path}:{number}: `{line.strip()}` is not `key: value`, `key:` or `  - item`. "
            "The file is flat on purpose."
        )

    unknown = sorted(set(values) - set(keys))
    if unknown:
        raise SetupError(f"{path}: unknown key {', '.join(unknown)}")
    missing = [key for key in keys if key not in values]
    if missing:
        raise SetupError(f"{path}: missing {', '.join(missing)}")
    for key in list_keys:
        if not isinstance(values[key], list):
            raise SetupError(f"{path}: `{key}` must be a list")
    return values


def _claim(values: dict[str, object], key: str, path: str, number: int) -> None:
    if key in values:
        raise SetupError(f"{path}:{number}: `{key}` is stated twice")


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _format_flat(choices: dict[str, object]) -> str:
    lines: list[str] = []
    for key, value in choices.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {item}" for item in value)
        else:
            lines.append(f"{key}: {value}" if value != "" else f"{key}: \"\"")
    return "\n".join(lines) + "\n"


def format_choices(answers: Answers) -> str:
    return _format_flat(answers.as_choices())


def format_local_choices(answers: Answers) -> str:
    """`.harnex/config.yml`'s own shape (design.md D2) — the same flat format, ten keys."""
    return _format_flat(answers.as_local_choices())


# --- templates and the pointer lines ------------------------------------------------

_TOKEN = re.compile(r"{{([a-z_]+)}}")
_POINTER_HEAD = re.compile(
    r"^<!-- position: (top|end) \| requires: (.+?) \| without: (.+) -->$"
)


@dataclass(frozen=True)
class Pointer:
    position: str
    requires: tuple[str, ...]
    without: str
    text: str

    def present_in(self, text: str) -> bool:
        return all(token in text for token in self.requires)

    def insert_into(self, text: str) -> str:
        body = self.text.rstrip("\n")
        if self.position == "top":
            return body + "\n\n" + text.lstrip("\n")
        return text.rstrip("\n") + "\n\n" + body + "\n"


def templates_dir(plugin_root: Path) -> Path:
    return plugin_root / "context" / "templates"


def load_pointer(plugin_root: Path, name: str) -> Pointer:
    path = templates_dir(plugin_root) / f"pointer-{name}.md"
    text = path.read_text(encoding="utf-8")
    first, _, rest = text.partition("\n")
    head = _POINTER_HEAD.match(first.strip())
    if not head:
        raise SetupError(
            f"{path}: the first line states where the line goes, what proves it is there "
            "and what is lost without it: "
            "`<!-- position: top|end | requires: … | without: … -->`"
        )
    requires = tuple(token.strip() for token in head.group(2).split(",") if token.strip())
    return Pointer(
        position=head.group(1),
        requires=requires,
        without=head.group(3).strip(),
        text=rest.strip("\n") + "\n",
    )


def render_template(plugin_root: Path, name: str, tokens: dict[str, str]) -> str:
    path = templates_dir(plugin_root) / name
    text = path.read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in tokens:
            raise SetupError(f"{path}: nothing answers `{{{{{key}}}}}`")
        return tokens[key]

    rendered = _TOKEN.sub(replace, text)
    left = _TOKEN.search(rendered)
    if left:
        raise SetupError(f"{path}: `{left.group(0)}` was left in the rendered file")
    return rendered


# --- the record ---------------------------------------------------------------------


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest_bytes(paths: dict[str, str], entries: dict[str, dict[str, list[str]]]) -> bytes:
    record = {"format": MANIFEST_FORMAT, "paths": paths, "entries": entries}
    return (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")


def read_manifest(project: Path) -> dict[str, object] | None:
    path = project / MANIFEST
    if not path.is_file():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SetupError(f"{MANIFEST}: the record is unreadable ({error})") from error
    if not isinstance(record, dict) or record.get("format") != MANIFEST_FORMAT:
        raise SetupError(
            f"{MANIFEST}: the record is of format {record.get('format') if isinstance(record, dict) else '?'}, "
            f"and this harness writes format {MANIFEST_FORMAT}"
        )
    record.setdefault("paths", {})
    record.setdefault("entries", {})
    return record


# --- the permission floor -----------------------------------------------------------


@dataclass(frozen=True)
class FloorEntry:
    rule: str
    list_name: str
    pattern: str


def load_floor(plugin_root: Path) -> list[FloorEntry]:
    path = plugin_root / "control" / "floor.json"
    try:
        floor = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SetupError(f"{path}: {error}") from error
    if floor.get("format") != FLOOR_FORMAT:
        raise SetupError(f"{path}: the floor is of a format this setup does not write")
    return [
        FloorEntry(rule=e["rule"], list_name=e["list"], pattern=e["pattern"])
        for e in floor["entries"]
    ]


def guard_only(plugin_root: Path) -> list[dict[str, str]]:
    path = plugin_root / "control" / "floor.json"
    return json.loads(path.read_text(encoding="utf-8")).get("guard_only", [])


def _split_rule(rule: str) -> tuple[str, str | None]:
    """`Bash(git push *)` -> (Bash, "git push *"); a bare `Bash` -> (Bash, None)."""
    if rule.endswith(")") and "(" in rule:
        tool, _, spec = rule.partition("(")
        return tool, spec[:-1]
    return rule, None


def _normalise(spec: str) -> str:
    """`ls:*` and `ls *` are the same rule; the colon form is only read at the end."""
    return spec[:-2] + " *" if spec.endswith(":*") else spec


def meets(allow: str, floor_pattern: str) -> bool:
    """Whether a project `allow` entry covers what a floor entry names."""
    allow_tool, allow_spec = _split_rule(allow)
    floor_tool, floor_spec = _split_rule(floor_pattern)
    if allow_tool != floor_tool or floor_spec is None:
        return allow_tool == floor_tool
    if allow_spec is None or allow_spec == "*":
        return True
    allow_spec, floor_spec = _normalise(allow_spec), _normalise(floor_spec)
    if allow_spec == floor_spec:
        return True
    if allow_spec.endswith("*"):
        return floor_spec.startswith(allow_spec[:-1])
    return False


# --- the survey and the plan --------------------------------------------------------

CREATE = "create"
UPDATE = "update"
UNCHANGED = "unchanged"
KEEP = "keep"
INSERT = "insert"
ADOPT = "adopt"
MERGE = "merge"
CONFLICT = "conflict"
MISSING = "missing"


@dataclass
class Step:
    path: str
    owner: str
    action: str
    detail: str
    data: bytes | None = None


@dataclass
class Plan:
    project: Path
    steps: list[Step] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    @property
    def writes(self) -> list[Step]:
        return [step for step in self.steps if step.data is not None]

    @property
    def nothing_to_do(self) -> bool:
        return not self.writes and not self.conflicts


def _read(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def build_plan(
    project: Path,
    plugin_root: Path,
    answers: Answers,
    mode: Literal["setup", "update"] = "setup",
    home: Path | None = None,
) -> Plan:
    """Survey every path, classify it by its content, and say what would happen to it.

    `home` only matters under local visibility (design.md D7's one global offer); it
    defaults to the real home directory and exists as a parameter purely so a test can
    stand a `tmp_path` in for it instead.
    """
    if answers.visibility == "local":
        return _build_local_plan(project, plugin_root, answers, mode, home or Path.home())

    plan = Plan(project=project)
    record = read_manifest(project)
    recorded_paths: dict[str, str] = dict(record["paths"]) if record else {}  # type: ignore[arg-type]

    rules = render_rules.render(
        list(answers.sets), list(answers.profiles), plugin_root / "context" / "rules"
    ).encode("utf-8")
    desired = {RULES: rules, STATE_IGNORE: STATE_IGNORE_BODY.encode("utf-8")}
    why = {
        RULES: "rendered from the sets the project chose",
        STATE_IGNORE: "the state directory ignores itself",
    }

    _plan_project_files(plan, project, plugin_root, answers, mode)
    _plan_harness_files(plan, project, answers, desired, why, recorded_paths, record is None)
    owned = _plan_settings(plan, project, plugin_root, record)
    mcp_owned = _plan_mcp(plan, project, plugin_root, answers, record)
    _plan_record(plan, project, desired, owned, mcp_owned)
    return plan


def _plan_project_files(
    plan: Plan,
    project: Path,
    plugin_root: Path,
    answers: Answers,
    mode: Literal["setup", "update"] = "setup",
) -> None:
    pointers = {
        AGENTS: (load_pointer(plugin_root, "agents"), answers.pointer_agents, "agents"),
        CLAUDE: (load_pointer(plugin_root, "claude"), answers.pointer_claude, "claude"),
    }
    tokens = {
        AGENTS: lambda: {
            "project_name": answers.project_name,
            "check_command": answers.check_command,
            "canary": canary_block(answers),
            "pointer_agents": pointers[AGENTS][0].text.rstrip("\n"),
        },
        CLAUDE: lambda: {
            "project_name": answers.project_name,
            "pointer_claude": pointers[CLAUDE][0].text.rstrip("\n"),
        },
        CHOICES: lambda: {"keys": format_choices(answers).rstrip("\n")},
        OPENSPEC_CONFIG: lambda: {},
    }
    templates = {
        AGENTS: AGENTS,
        CLAUDE: CLAUDE,
        CHOICES: "harnex.yml",
        OPENSPEC_CONFIG: "openspec-config.yaml",
    }

    for path in PROJECT_PATHS:
        current = _read(project / path)
        if current is None:
            if mode == "update":
                plan.steps.append(
                    Step(path, "project", MISSING, f"{path} is missing; setup creates it")
                )
                plan.notices.append(
                    f"{path} is missing. Update never creates a project-owned file; "
                    "run setup to create it."
                )
                continue
            body = render_template(plugin_root, templates[path], tokens[path]())
            plan.steps.append(
                Step(path, "project", CREATE, "from the harness's template", body.encode("utf-8"))
            )
            continue
        if path not in pointers:
            plan.steps.append(Step(path, "project", KEEP, "the project's own, left alone"))
            continue

        pointer, approved, _ = pointers[path]
        text = current.decode("utf-8", errors="replace")
        if pointer.present_in(text):
            plan.steps.append(Step(path, "project", KEEP, "already points at the rules"))
        elif approved:
            plan.steps.append(
                Step(
                    path,
                    "project",
                    INSERT,
                    f"the pointer line, at the {pointer.position} of the file",
                    pointer.insert_into(text).encode("utf-8"),
                )
            )
        else:
            plan.steps.append(
                Step(path, "project", KEEP, "the project's own, and it does not point at the rules")
            )
            plan.notices.append(
                f"{path} does not point at {RULES}. Until the line is there, "
                f"{pointer.without}. It goes at the {pointer.position} of the file:\n"
                + "\n".join(
                    ("    " + line).rstrip() for line in pointer.text.rstrip("\n").splitlines()
                )
            )

    _maybe_jev_notice(plan, answers)


def _maybe_jev_notice(plan: Plan, answers: Answers) -> None:
    if answers.decision_model == "jev":
        plan.notices.append(
            f"{ENV_FILE} at the project root is where the `jev` backend falls back to look "
            "for the key when the environment variable is unset. It must declare the line "
            "`OPENROUTER_API_KEY=` followed by the value, and it is the person's own "
            f"responsibility to keep {ENV_FILE} out of version control. Setup does not "
            f"read, write, or gitignore {ENV_FILE} itself."
        )


def _plan_harness_files(
    plan: Plan,
    project: Path,
    answers: Answers,
    desired: dict[str, bytes],
    why: dict[str, str],
    recorded: dict[str, str],
    no_record: bool,
) -> None:
    for path, body in desired.items():
        current = _read(project / path)
        if current is None:
            plan.steps.append(Step(path, "harness", CREATE, why[path], body))
        elif current == body:
            plan.steps.append(Step(path, "harness", UNCHANGED, "already what the harness writes"))
        elif recorded.get(path) == digest(current):
            plan.steps.append(
                Step(path, "harness", UPDATE, "the harness wrote it; the rendering changed", body)
            )
        elif path in answers.adopt:
            plan.steps.append(Step(path, "harness", ADOPT, "replaced by the harness's rendering", body))
        else:
            plan.steps.append(Step(path, "harness", CONFLICT, "present, and the harness did not write it"))
            reason = (
                "there is no record of what the harness generated"
                if no_record
                else "it was edited after the harness wrote it"
            )
            plan.conflicts.append(
                f"{path} is a path the harness owns, but {reason}. Move it aside and run "
                "setup again, or approve its adoption and the harness will replace it with "
                "its own rendering."
            )


def _plan_settings(
    plan: Plan,
    project: Path,
    plugin_root: Path,
    record: dict[str, object] | None,
    *,
    target: str = SETTINGS,
    owner: str = "shared",
) -> dict[str, list[str]]:
    """Merge the permission floor into `target` (`.claude/settings.json`, shared, or —
    under local visibility — `.claude/settings.local.json`, design.md D3), entry by
    entry, the same way either file is merged."""
    floor = load_floor(plugin_root)
    wanted: dict[str, list[str]] = {"deny": [], "ask": []}
    for entry in floor:
        wanted[entry.list_name].append(entry.pattern)

    path = project / target
    current = _read(path)
    if current is None:
        merged = {"permissions": {"deny": list(wanted["deny"]), "ask": list(wanted["ask"])}}
        plan.steps.append(
            Step(
                target,
                owner,
                CREATE,
                f"{len(wanted['deny']) + len(wanted['ask'])} floor entries",
                _settings_bytes(merged),
            )
        )
        return {name: sorted(patterns) for name, patterns in wanted.items()}

    try:
        settings = json.loads(current.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        plan.steps.append(Step(target, owner, CONFLICT, "cannot be read as JSON"))
        plan.conflicts.append(
            f"{target} cannot be read as JSON ({error}). The floor is merged entry by "
            "entry, never as text, so the file has to be readable first."
        )
        return {"deny": [], "ask": []}
    if not isinstance(settings, dict):
        plan.steps.append(Step(target, owner, CONFLICT, "is not an object"))
        plan.conflicts.append(f"{target} is not a JSON object, so it holds no entries to merge.")
        return {"deny": [], "ask": []}

    merged = json.loads(json.dumps(settings))
    permissions = merged.setdefault("permissions", {})
    if not isinstance(permissions, dict):
        plan.steps.append(Step(target, owner, CONFLICT, "`permissions` is not an object"))
        plan.conflicts.append(f"{target}: `permissions` is not an object.")
        return {"deny": [], "ask": []}

    added: dict[str, list[str]] = {"deny": [], "ask": []}
    for name, patterns in wanted.items():
        existing = permissions.setdefault(name, [])
        if not isinstance(existing, list):
            plan.steps.append(Step(target, owner, CONFLICT, f"`permissions.{name}` is not a list"))
            plan.conflicts.append(f"{target}: `permissions.{name}` is not a list of entries.")
            return {"deny": [], "ask": []}
        for pattern in patterns:
            if pattern not in existing:
                existing.append(pattern)
                added[name].append(pattern)

    _notice_overlaps(plan, permissions, wanted, target)
    _notice_bypass(plan, permissions, target)

    previously: dict[str, list[str]] = {"deny": [], "ask": []}
    kept = record["entries"].get(target, {}) if record else {}  # type: ignore[union-attr]
    for name in previously:
        previously[name] = [p for p in kept.get(name, []) if p in permissions.get(name, [])]

    if not any(previously.values()) and merged == settings:
        # Recovery by content, as for a file: nothing is missing, so what is there is what
        # the harness writes. An interruption after this file and before the record leaves
        # exactly this state, and forgetting the entries would leave them unowned forever.
        previously = {name: list(patterns) for name, patterns in wanted.items()}

    owned = {
        name: sorted(set(previously[name]) | set(added[name])) for name in ("deny", "ask")
    }

    if merged == settings:
        plan.steps.append(Step(target, owner, UNCHANGED, "the floor is already there"))
    else:
        plan.steps.append(
            Step(
                target,
                owner,
                MERGE,
                f"{len(added['deny']) + len(added['ask'])} floor entries added, "
                f"every other entry kept",
                _settings_bytes(merged),
            )
        )
    return owned


def _settings_bytes(settings: dict[str, object]) -> bytes:
    return (json.dumps(settings, indent=2) + "\n").encode("utf-8")


def _recorded_mcp_entries(record: dict[str, object] | None) -> dict[str, list[str]]:
    """Keep this shared file's recorded ownership when a UI profile is later removed."""
    entries = record.get("entries", {}) if record else {}
    owned = entries.get(MCP_CONFIG, {}) if isinstance(entries, dict) else {}
    servers = owned.get("mcpServers", []) if isinstance(owned, dict) else []
    return {"mcpServers": ["playwright"]} if "playwright" in servers else {}


def _mcp_entry_notice() -> str:
    return json.dumps({"mcpServers": {"playwright": PLAYWRIGHT_MCP}}, indent=2)


def _plan_mcp(
    plan: Plan,
    project: Path,
    plugin_root: Path,
    answers: Answers,
    record: dict[str, object] | None,
) -> dict[str, list[str]]:
    """Offer the Playwright server only to projects that currently choose a UI profile."""
    if not any(profile in ui_profiles(plugin_root) for profile in answers.profiles):
        return _recorded_mcp_entries(record)

    current = _read(project / MCP_CONFIG)
    if current is None:
        if answers.mcp_playwright:
            plan.steps.append(
                Step(
                    MCP_CONFIG,
                    "shared",
                    CREATE,
                    "the Playwright MCP entry",
                    _settings_bytes({"mcpServers": {"playwright": PLAYWRIGHT_MCP}}),
                )
            )
            return {"mcpServers": ["playwright"]}
        plan.steps.append(Step(MCP_CONFIG, "shared", KEEP, "no Playwright MCP entry yet"))
        plan.notices.append(
            f"{MCP_CONFIG} has no Playwright MCP entry. It would add:\n"
            + "\n".join("    " + line for line in _mcp_entry_notice().splitlines())
        )
        return {}

    try:
        config = json.loads(current.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        plan.steps.append(Step(MCP_CONFIG, "shared", CONFLICT, "cannot be read as JSON"))
        plan.conflicts.append(
            f"{MCP_CONFIG} cannot be read as JSON ({error}). The Playwright entry is merged "
            "by key, never as text, so the file has to be readable first."
        )
        return {}
    if not isinstance(config, dict):
        plan.steps.append(Step(MCP_CONFIG, "shared", CONFLICT, "is not an object"))
        plan.conflicts.append(f"{MCP_CONFIG} is not a JSON object, so it holds no entries to merge.")
        return {}

    merged = copy.deepcopy(config)
    servers = merged.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        plan.steps.append(Step(MCP_CONFIG, "shared", CONFLICT, "`mcpServers` is not an object"))
        plan.conflicts.append(f"{MCP_CONFIG}: `mcpServers` is not an object.")
        return {}

    if "playwright" in servers:
        owned = _recorded_mcp_entries(record)
        if not owned and servers["playwright"] == PLAYWRIGHT_MCP:
            owned = {"mcpServers": ["playwright"]}
        detail = (
            "already carries the Playwright MCP entry"
            if owned
            else 'a different "playwright" entry already exists; left alone'
        )
        plan.steps.append(Step(MCP_CONFIG, "shared", KEEP, detail))
        return owned

    if answers.mcp_playwright:
        servers["playwright"] = PLAYWRIGHT_MCP
        plan.steps.append(
            Step(
                MCP_CONFIG,
                "shared",
                MERGE,
                "the Playwright MCP entry added, every other entry kept",
                _settings_bytes(merged),
            )
        )
        return {"mcpServers": ["playwright"]}

    plan.steps.append(Step(MCP_CONFIG, "shared", KEEP, "no Playwright MCP entry yet"))
    plan.notices.append(
        f"{MCP_CONFIG} has no Playwright MCP entry. It would add:\n"
        + "\n".join("    " + line for line in _mcp_entry_notice().splitlines())
    )
    return {}


def _notice_overlaps(
    plan: Plan, permissions: dict[str, object], wanted: dict[str, list[str]], target: str = SETTINGS
) -> None:
    allows = permissions.get("allow", [])
    if not isinstance(allows, list):
        return
    for allow in allows:
        if not isinstance(allow, str):
            continue
        met = [p for patterns in wanted.values() for p in patterns if meets(allow, p)]
        if not met:
            continue
        _, spec = _split_rule(allow)
        breadth = "covers every use of the tool" if spec in (None, "*") else "covers"
        plan.notices.append(
            f"{target}: your allow entry `{allow}` {breadth} "
            f"{len(met)} floor entr{'y' if len(met) == 1 else 'ies'}, such as `{met[0]}`. "
            "The host resolves deny, then ask, then allow, and a more specific allow does "
            "not carve an exception out of either, so the floor still applies and your "
            "entry has no effect on those commands."
        )


def _notice_bypass(plan: Plan, permissions: dict[str, object], target: str = SETTINGS) -> None:
    mode = permissions.get("defaultMode")
    if isinstance(mode, str) and mode in BYPASS_MODES:
        plan.notices.append(
            f"{target}: `permissions.defaultMode` is `{mode}`, which bypasses permissions "
            "altogether. The floor is written, and in that mode nothing of it is in force. "
            "No harness can defend against it."
        )


# --- local visibility (docs/PLAN.md C7): every path below, project-prefixed or not,
# is local-visibility-only and leaves `shared` visibility (above) untouched -------------


def _plan_local_entry_files(plan: Plan, project: Path) -> None:
    """`AGENTS.md`/`CLAUDE.md` are reported, never touched (project-setup's own MODIFIED
    requirement) — every surveyed path appears in the plan, even one the command will
    never write, per the unmodified "Setup prints a plan, one line per path" requirement.
    """
    for path in (AGENTS, CLAUDE):
        current = _read(project / path)
        detail = (
            "the project's own; local visibility never touches it"
            if current is not None
            else "absent; local visibility never creates it"
        )
        plan.steps.append(Step(path, "project", KEEP, detail))


def _plan_local_config(
    plan: Plan, project: Path, plugin_root: Path, answers: Answers, mode: str
) -> None:
    """`.harnex/config.yml`, local visibility's own answers file (design.md D2) — created
    once, from the template, exactly like `.harnex.yml` under `shared` visibility, and
    never rewritten afterward."""
    current = _read(project / LOCAL_CHOICES)
    if current is None:
        if mode == "update":
            plan.steps.append(
                Step(LOCAL_CHOICES, "project", MISSING, f"{LOCAL_CHOICES} is missing; setup creates it")
            )
            plan.notices.append(
                f"{LOCAL_CHOICES} is missing. Update never creates a project-owned file; "
                "run setup to create it."
            )
        else:
            body = render_template(
                plugin_root, "local-config.yml", {"keys": format_local_choices(answers).rstrip("\n")}
            )
            plan.steps.append(
                Step(LOCAL_CHOICES, "project", CREATE, "from the harness's template", body.encode("utf-8"))
            )
    else:
        plan.steps.append(Step(LOCAL_CHOICES, "project", KEEP, "the project's own, left alone"))

    _maybe_jev_notice(plan, answers)


# Every local-visibility path that cannot live inside a self-ignoring directory
# (`.harnex/`'s own) — so each needs its own `.git/info/exclude` entry instead.
GIT_EXCLUDE_PATHS = (CLAUDE_LOCAL, SETTINGS_LOCAL)


def _plan_git_exclude(plan: Plan, project: Path) -> None:
    """Keep every root-level local-visibility path out of git without ever touching the
    project's own ignore file (local-visibility spec: "a path that cannot live inside [a
    self-ignoring directory]... excluded through an entry the harness adds to
    `.git/info/exclude`")."""
    if not (project / ".git").is_dir():
        plan.steps.append(Step(GIT_EXCLUDE, "local", CONFLICT, "no .git directory here"))
        plan.conflicts.append(
            f"Local visibility excludes {', '.join(GIT_EXCLUDE_PATHS)} through "
            f"{GIT_EXCLUDE}, which needs a git repository. Run `git init` first, or "
            "choose `shared` visibility."
        )
        return

    exclude_path = project / GIT_EXCLUDE
    current = _read(exclude_path)
    text = current.decode("utf-8", errors="replace") if current is not None else ""
    existing = set(text.splitlines())
    missing = [path for path in GIT_EXCLUDE_PATHS if path not in existing]
    if not missing:
        plan.steps.append(
            Step(GIT_EXCLUDE, "local", UNCHANGED, f"{', '.join(GIT_EXCLUDE_PATHS)} already excluded")
        )
        return

    new_text = text if (not text or text.endswith("\n")) else text + "\n"
    new_text += "".join(f"{path}\n" for path in missing)
    action = CREATE if current is None else UPDATE
    plan.steps.append(
        Step(
            GIT_EXCLUDE,
            "local",
            action,
            f"{', '.join(missing)} added to the repository's own local exclude list",
            new_text.encode("utf-8"),
        )
    )


def _plan_local_mcp_notice(plan: Plan, plugin_root: Path, answers: Answers) -> None:
    """No file is written for an MCP entry under local visibility (design.md D4) — just
    the exact command to run, the same "show, write only after yes" discipline, carried
    out by the skill rather than by this script."""
    if not any(profile in ui_profiles(plugin_root) for profile in answers.profiles):
        return
    plan.steps.append(Step(MCP_CONFIG, "local", KEEP, "local visibility never writes .mcp.json"))
    plan.notices.append(
        f"A UI profile is chosen. Under local visibility the Playwright MCP entry is "
        f"never written to {MCP_CONFIG}; register it locally instead, after your yes:\n"
        "    claude mcp add playwright --scope local -- npx @playwright/mcp@latest"
    )


def _plan_local_store(plan: Plan, answers: Answers) -> None:
    """No file inside the project names the store (design.md D5) — this is purely the
    plan's own transparency line, the same "every surveyed path says what happens to it"
    principle extended to the one piece of local visibility that lives outside any path
    at all."""
    plan.steps.append(
        Step(
            "openspec store",
            "local",
            UNCHANGED,
            f"this project's own propose/apply/verify/ship work uses store "
            f"`{answers.store_id}`",
        )
    )


_INSTRUCTION_FILES_TARGET = "claude-md-and-agents-md"


def _plan_global_instructions(plan: Plan, home: Path, answers: Answers) -> None:
    """The one-time, machine-wide offer local visibility depends on (design.md D7):
    without it, a project's own `CLAUDE.local.md` stops Claude Code from reading that
    project's `AGENTS.md`. Never offered under `shared` visibility, and never written
    without the person's own explicit yes."""
    path = home / GLOBAL_SETTINGS
    label = str(path)
    current = _read(path)
    settings: dict[str, object] = {}
    if current is not None:
        try:
            settings = json.loads(current.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            plan.steps.append(Step(label, "home", CONFLICT, "cannot be read as JSON"))
            plan.conflicts.append(f"{label} cannot be read as JSON ({error}).")
            return
        if not isinstance(settings, dict):
            plan.steps.append(Step(label, "home", CONFLICT, "is not an object"))
            plan.conflicts.append(f"{label} is not a JSON object.")
            return

    plugin_configs = settings.get("pluginConfigs", {})
    if not isinstance(plugin_configs, dict):
        plan.steps.append(Step(label, "home", CONFLICT, "`pluginConfigs` is not an object"))
        plan.conflicts.append(f"{label}: `pluginConfigs` is not an object.")
        return
    agents_md = plugin_configs.get("agents-md@builtin", {})
    if not isinstance(agents_md, dict):
        plan.steps.append(Step(label, "home", CONFLICT, "`pluginConfigs.\"agents-md@builtin\"` is not an object"))
        plan.conflicts.append(f'{label}: `pluginConfigs."agents-md@builtin"` is not an object.')
        return
    options = agents_md.get("options", {})
    if not isinstance(options, dict):
        plan.steps.append(Step(label, "home", CONFLICT, "...options is not an object"))
        plan.conflicts.append(f'{label}: `pluginConfigs."agents-md@builtin".options` is not an object.')
        return

    if options.get("instructionFiles") == _INSTRUCTION_FILES_TARGET:
        plan.steps.append(
            Step(label, "home", UNCHANGED, "AGENTS.md already keeps loading alongside CLAUDE.local.md")
        )
        return

    if not answers.global_instructions:
        plan.steps.append(Step(label, "home", KEEP, "not yet approved this run"))
        plan.notices.append(
            f"{label}: without `pluginConfigs.\"agents-md@builtin\".options.instructionFiles` "
            f'set to "{_INSTRUCTION_FILES_TARGET}", this project\'s own {CLAUDE_LOCAL} will '
            "stop Claude Code from reading its AGENTS.md (projects with no CLAUDE.md of "
            "their own). This is a one-time, machine-wide setting, not specific to this "
            "project — approve it once and every project benefits. Declining leaves this "
            f"project's {AGENTS} unread the moment {CLAUDE_LOCAL} exists, and this notice "
            "returns on every later run until the setting is there."
        )
        return

    merged = copy.deepcopy(settings)
    merged.setdefault("pluginConfigs", {})
    merged["pluginConfigs"].setdefault("agents-md@builtin", {})
    merged["pluginConfigs"]["agents-md@builtin"].setdefault("options", {})
    merged["pluginConfigs"]["agents-md@builtin"]["options"]["instructionFiles"] = _INSTRUCTION_FILES_TARGET
    plan.steps.append(
        Step(
            label,
            "home",
            MERGE,
            "instructionFiles set so AGENTS.md keeps loading alongside CLAUDE.local.md",
            _settings_bytes(merged),
        )
    )


def _build_local_plan(
    project: Path,
    plugin_root: Path,
    answers: Answers,
    mode: Literal["setup", "update"],
    home: Path,
) -> Plan:
    """Local visibility's own plan (docs/PLAN.md C7, design.md): every path either lives
    inside a self-ignoring directory, is excluded through `.git/info/exclude`, or — for
    the floor and the one global offer — is a file this script already knows how to merge,
    just at a different target. `AGENTS.md`, `CLAUDE.md`, `openspec/config.yaml`,
    `.claude/settings.json` and `.mcp.json` are never written by any of it."""
    plan = Plan(project=project)
    record = read_manifest(project)
    recorded_paths: dict[str, str] = dict(record["paths"]) if record else {}  # type: ignore[arg-type]

    rules = render_rules.render(
        list(answers.sets), list(answers.profiles), plugin_root / "context" / "rules"
    ).encode("utf-8")
    claude_local = render_template(plugin_root, CLAUDE_LOCAL, {})
    desired = {
        RULES: rules,
        HARNEX_IGNORE: HARNEX_IGNORE_BODY.encode("utf-8"),
        CLAUDE_LOCAL: claude_local.encode("utf-8"),
    }
    why = {
        RULES: "rendered from the sets the project chose",
        HARNEX_IGNORE: "the whole of .harnex/ ignores itself under local visibility",
        CLAUDE_LOCAL: "the one import local visibility ever writes",
    }

    _plan_local_entry_files(plan, project)
    _plan_local_config(plan, project, plugin_root, answers, mode)
    _plan_harness_files(plan, project, answers, desired, why, recorded_paths, record is None)
    _plan_git_exclude(plan, project)
    owned = _plan_settings(plan, project, plugin_root, record, target=SETTINGS_LOCAL, owner="local")
    _plan_local_mcp_notice(plan, plugin_root, answers)
    _plan_local_store(plan, answers)
    if mode == "setup":
        _plan_global_instructions(plan, home, answers)
    _plan_record(plan, project, desired, owned, {})
    return plan


def _plan_record(
    plan: Plan,
    project: Path,
    desired: dict[str, bytes],
    owned: dict[str, list[str]],
    mcp_owned: dict[str, list[str]],
) -> None:
    paths = {path: digest(body) for path, body in sorted(desired.items())}
    entries = {SETTINGS: owned} if owned["deny"] or owned["ask"] else {}
    if mcp_owned:
        entries[MCP_CONFIG] = mcp_owned
    body = manifest_bytes(paths, entries)
    current = _read(project / MANIFEST)
    if current == body:
        plan.steps.append(Step(MANIFEST, "harness", UNCHANGED, "the record already says this"))
    else:
        plan.steps.append(
            Step(
                MANIFEST,
                "harness",
                CREATE if current is None else UPDATE,
                "what the harness generated, written last",
                body,
            )
        )


# --- writing ------------------------------------------------------------------------


def write_atomic(path: Path, data: bytes) -> None:
    """Somewhere else, then one rename: an interruption never leaves a fragment."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as sink:
            sink.write(data)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def apply_plan(plan: Plan) -> list[str]:
    if plan.conflicts:
        raise SetupError("the plan has conflicts, so nothing was written")
    written = []
    for step in plan.steps:
        if step.data is None:
            continue
        # Every step's path is project-relative, except local visibility's one global
        # offer (design.md D7), which names an absolute path outside the project.
        target = Path(step.path) if Path(step.path).is_absolute() else plan.project / step.path
        write_atomic(target, step.data)
        written.append(step.path)
    return written


# --- saying what it found -----------------------------------------------------------


def render_plan(plan: Plan, verb: str = "plan") -> str:
    lines = [f"Plan for {plan.project}", ""]
    width = max(len(step.path) for step in plan.steps)
    for step in plan.steps:
        lines.append(f"  {step.action:<9} {step.path:<{width}}  {step.owner:<7}  {step.detail}")
    if plan.notices:
        lines += ["", "Notices"]
        for notice in plan.notices:
            lines.append("  - " + notice.replace("\n", "\n    "))
    if plan.conflicts:
        lines += ["", "Conflicts — nothing is written while one of these stands"]
        for conflict in plan.conflicts:
            lines.append("  - " + conflict)
    lines += [""]
    if plan.conflicts:
        lines.append(f"{len(plan.conflicts)} conflict(s). Resolve them and run setup again.")
    elif plan.nothing_to_do:
        lines.append("Nothing to do: this project is already set up as these answers describe.")
    elif verb == "write":
        lines.append(f"{len(plan.writes)} path(s) to write.")
    else:
        lines.append(
            f"{len(plan.writes)} path(s) would be written. Nothing has been written yet."
        )
    return "\n".join(lines) + "\n"


def plan_as_json(plan: Plan) -> str:
    return json.dumps(
        {
            "project": str(plan.project),
            "nothing_to_do": plan.nothing_to_do,
            "steps": [
                {
                    "path": step.path,
                    "owner": step.owner,
                    "action": step.action,
                    "detail": step.detail,
                    "writes": step.data is not None,
                }
                for step in plan.steps
            ],
            "notices": plan.notices,
            "conflicts": plan.conflicts,
        },
        indent=2,
    )


# --- the command line ---------------------------------------------------------------


def default_plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Survey a project, plan what setup would do, and write it after a yes."
    )
    parser.add_argument("verb", choices=("choices", "plan", "write"))
    parser.add_argument("--answers", help="the answers document, or - for stdin")
    parser.add_argument("--project", default=".", help="the project to set up")
    parser.add_argument("--plugin-root", default=None, help="where the harness is installed")
    parser.add_argument(
        "--home", default=None, help="the home directory (local visibility's one global offer)"
    )
    parser.add_argument("--json", action="store_true", help="print the plan as JSON")
    args = parser.parse_args(argv)

    project = Path(args.project).resolve()
    plugin_root = Path(args.plugin_root).resolve() if args.plugin_root else default_plugin_root()
    home = Path(args.home).resolve() if args.home else None

    try:
        if args.verb == "choices":
            print(json.dumps(choices_on_offer(plugin_root), indent=2))
            return 0
        if not args.answers:
            parser.error("--answers is required to plan or write")
        text = sys.stdin.read() if args.answers == "-" else Path(args.answers).read_text("utf-8")
        answers = read_answers(text, plugin_root)
        plan = build_plan(project, plugin_root, answers, home=home)
        if args.json:
            print(plan_as_json(plan))
        else:
            print(render_plan(plan, args.verb), end="")
        if plan.conflicts:
            return 1
        if args.verb == "write":
            written = apply_plan(plan)
            if not args.json:
                print("" if not written else "Written: " + ", ".join(written))
    except (SetupError, render_rules.RuleError) as error:
        print(f"setup: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"setup: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
