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
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

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

PROJECT_PATHS = (AGENTS, CLAUDE, CHOICES, OPENSPEC_CONFIG)
HARNESS_PATHS = (RULES, STATE_IGNORE)

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
LIST_KEYS = ("profiles", "sets", "features")
DECISION_BACKENDS = ("mock", "jev")

STATE_IGNORE_BODY = """\
# Runtime state the harness writes while it works: decision journal, apply run state.
# It ignores itself so that the project's own ignore file is never touched.
*
"""

MANIFEST_FORMAT = 1
FLOOR_FORMAT = 1

BYPASS_MODES = ("bypassPermissions",)

# What setup proposes when a project chooses the canary set. The word itself is the
# project's to change; the proposal lives here so that no command has to remember it.
DEFAULT_CANARY = "Hullaballoo!"


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
    adopt: tuple[str, ...] = ()

    def as_choices(self) -> dict[str, object]:
        """Only the seven the project records; the approvals are this run's, not the
        project's."""
        return {
            "project_name": self.project_name,
            "profiles": list(self.profiles),
            "sets": list(self.sets),
            "features": list(self.features),
            "canary": self.canary,
            "decision_model": self.decision_model,
            "check_command": self.check_command,
        }


def available_sets(plugin_root: Path) -> list[str]:
    return render_rules.available_sets(plugin_root / "context" / "rules")


def available_profiles(plugin_root: Path) -> list[str]:
    """The profiles the harness holds. None, until a change adds the first one."""
    directory = plugin_root / "tools" / "profiles"
    if not directory.is_dir():
        return []
    return sorted(p.name for p in directory.iterdir() if p.is_dir())


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
    unknown_keys = sorted(set(raw) - set(ANSWER_KEYS) - {"approvals"})
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
        adopt=tuple(approvals.get("adopt", ()) or ()),
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
    for path in answers.adopt:
        if path not in HARNESS_PATHS:
            raise SetupError(f"{path} is not a path the harness owns, so it cannot adopt it")


def choices_on_offer(plugin_root: Path) -> dict[str, object]:
    """What a project may choose, derived from what the harness holds, not from a list."""
    return {
        "sets": available_sets(plugin_root),
        "profiles": available_profiles(plugin_root),
        "features": available_features(plugin_root),
        "decision_models": list(DECISION_BACKENDS),
        "default_canary": DEFAULT_CANARY,
    }


# --- the project's choices file, written and read as one flat shape -----------------

_SCALAR = re.compile(r"^([a-z][a-z_]*): +(\S.*?)\s*$")
_LIST_HEAD = re.compile(r"^([a-z][a-z_]*):\s*$")
_LIST_ITEM = re.compile(r"^ +- +(\S.*?)\s*$")


def parse_choices(text: str, path: str = CHOICES) -> dict[str, object]:
    """The reader is the schema: what it does not understand, it refuses, with the line."""
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

    unknown = sorted(set(values) - set(ANSWER_KEYS))
    if unknown:
        raise SetupError(f"{path}: unknown key {', '.join(unknown)}")
    missing = [key for key in ANSWER_KEYS if key not in values]
    if missing:
        raise SetupError(f"{path}: missing {', '.join(missing)}")
    for key in LIST_KEYS:
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


def format_choices(answers: Answers) -> str:
    lines: list[str] = []
    for key, value in answers.as_choices().items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {item}" for item in value)
        else:
            lines.append(f"{key}: {value}" if value != "" else f"{key}: \"\"")
    return "\n".join(lines) + "\n"


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


def build_plan(project: Path, plugin_root: Path, answers: Answers) -> Plan:
    """Survey every path, classify it by its content, and say what would happen to it."""
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

    _plan_project_files(plan, project, plugin_root, answers)
    _plan_harness_files(plan, project, answers, desired, why, recorded_paths, record is None)
    owned = _plan_settings(plan, project, plugin_root, record)
    _plan_record(plan, project, desired, owned)
    return plan


def _plan_project_files(
    plan: Plan, project: Path, plugin_root: Path, answers: Answers
) -> None:
    pointers = {
        AGENTS: (load_pointer(plugin_root, "agents"), answers.pointer_agents, "agents"),
        CLAUDE: (load_pointer(plugin_root, "claude"), answers.pointer_claude, "claude"),
    }
    tokens = {
        AGENTS: lambda: {
            "project_name": answers.project_name,
            "check_command": answers.check_command,
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
    plan: Plan, project: Path, plugin_root: Path, record: dict[str, object] | None
) -> dict[str, list[str]]:
    floor = load_floor(plugin_root)
    wanted: dict[str, list[str]] = {"deny": [], "ask": []}
    for entry in floor:
        wanted[entry.list_name].append(entry.pattern)

    path = project / SETTINGS
    current = _read(path)
    if current is None:
        merged = {"permissions": {"deny": list(wanted["deny"]), "ask": list(wanted["ask"])}}
        plan.steps.append(
            Step(
                SETTINGS,
                "shared",
                CREATE,
                f"{len(wanted['deny']) + len(wanted['ask'])} floor entries",
                _settings_bytes(merged),
            )
        )
        return {name: sorted(patterns) for name, patterns in wanted.items()}

    try:
        settings = json.loads(current.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        plan.steps.append(Step(SETTINGS, "shared", CONFLICT, "cannot be read as JSON"))
        plan.conflicts.append(
            f"{SETTINGS} cannot be read as JSON ({error}). The floor is merged entry by "
            "entry, never as text, so the file has to be readable first."
        )
        return {"deny": [], "ask": []}
    if not isinstance(settings, dict):
        plan.steps.append(Step(SETTINGS, "shared", CONFLICT, "is not an object"))
        plan.conflicts.append(f"{SETTINGS} is not a JSON object, so it holds no entries to merge.")
        return {"deny": [], "ask": []}

    merged = json.loads(json.dumps(settings))
    permissions = merged.setdefault("permissions", {})
    if not isinstance(permissions, dict):
        plan.steps.append(Step(SETTINGS, "shared", CONFLICT, "`permissions` is not an object"))
        plan.conflicts.append(f"{SETTINGS}: `permissions` is not an object.")
        return {"deny": [], "ask": []}

    added: dict[str, list[str]] = {"deny": [], "ask": []}
    for name, patterns in wanted.items():
        existing = permissions.setdefault(name, [])
        if not isinstance(existing, list):
            plan.steps.append(Step(SETTINGS, "shared", CONFLICT, f"`permissions.{name}` is not a list"))
            plan.conflicts.append(f"{SETTINGS}: `permissions.{name}` is not a list of entries.")
            return {"deny": [], "ask": []}
        for pattern in patterns:
            if pattern not in existing:
                existing.append(pattern)
                added[name].append(pattern)

    _notice_overlaps(plan, permissions, wanted)
    _notice_bypass(plan, permissions)

    previously: dict[str, list[str]] = {"deny": [], "ask": []}
    kept = record["entries"].get(SETTINGS, {}) if record else {}  # type: ignore[union-attr]
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
        plan.steps.append(Step(SETTINGS, "shared", UNCHANGED, "the floor is already there"))
    else:
        plan.steps.append(
            Step(
                SETTINGS,
                "shared",
                MERGE,
                f"{len(added['deny']) + len(added['ask'])} floor entries added, "
                f"every other entry kept",
                _settings_bytes(merged),
            )
        )
    return owned


def _settings_bytes(settings: dict[str, object]) -> bytes:
    return (json.dumps(settings, indent=2) + "\n").encode("utf-8")


def _notice_overlaps(plan: Plan, permissions: dict[str, object], wanted: dict[str, list[str]]) -> None:
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
            f"{SETTINGS}: your allow entry `{allow}` {breadth} "
            f"{len(met)} floor entr{'y' if len(met) == 1 else 'ies'}, such as `{met[0]}`. "
            "The host resolves deny, then ask, then allow, and a more specific allow does "
            "not carve an exception out of either, so the floor still applies and your "
            "entry has no effect on those commands."
        )


def _notice_bypass(plan: Plan, permissions: dict[str, object]) -> None:
    mode = permissions.get("defaultMode")
    if isinstance(mode, str) and mode in BYPASS_MODES:
        plan.notices.append(
            f"{SETTINGS}: `permissions.defaultMode` is `{mode}`, which bypasses permissions "
            "altogether. The floor is written, and in that mode nothing of it is in force. "
            "No harness can defend against it."
        )


def _plan_record(
    plan: Plan, project: Path, desired: dict[str, bytes], owned: dict[str, list[str]]
) -> None:
    paths = {path: digest(body) for path, body in sorted(desired.items())}
    entries = {SETTINGS: owned} if owned["deny"] or owned["ask"] else {}
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
        write_atomic(plan.project / step.path, step.data)
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
    parser.add_argument("--json", action="store_true", help="print the plan as JSON")
    args = parser.parse_args(argv)

    project = Path(args.project).resolve()
    plugin_root = Path(args.plugin_root).resolve() if args.plugin_root else default_plugin_root()

    try:
        if args.verb == "choices":
            print(json.dumps(choices_on_offer(plugin_root), indent=2))
            return 0
        if not args.answers:
            parser.error("--answers is required to plan or write")
        text = sys.stdin.read() if args.answers == "-" else Path(args.answers).read_text("utf-8")
        answers = read_answers(text, plugin_root)
        plan = build_plan(project, plugin_root, answers)
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
