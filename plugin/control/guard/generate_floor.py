#!/usr/bin/env python3
"""Generate the committed permission floor from the guard's pattern source.

``patterns.yaml`` is YAML-shaped rather than YAML: it is an ordered list of flat
records.  Keeping this parser here avoids making a maintainer command depend on a
YAML package just to regenerate JSON.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable


FORMAT = 1
VERIFIED_AGAINST = "Claude Code 2.1.269"
NOTE = (
    "The floor states what the harness's own rules state, in the host's permission "
    "syntax, and nothing more: a rule that says ask becomes an ask entry, and deny is "
    "used only where reading could never be part of a project's work. Every entry names "
    "the rule it comes from, so a check can walk from a rule to its coverage and back. "
    "Order matters: a pattern beginning with ! carves paths out of the entries listed "
    "before it."
)

_FIRST_FIELD = re.compile(r"^- ([a-z][a-z_]*): +(\S.*?)\s*$")
_FIELD = re.compile(r"^  ([a-z][a-z_]*): +(\S.*?)\s*$")


class PatternError(ValueError):
    """The flat pattern source does not have the shape this generator understands."""


def _value(raw: str, path: Path, line_number: int) -> str:
    """Read a YAML-shaped scalar, including the JSON-style quoted strings in the file."""
    if not raw.startswith('"'):
        return raw
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise PatternError(f"{path}:{line_number}: invalid quoted value: {error.msg}") from error
    if not isinstance(value, str):
        raise PatternError(f"{path}:{line_number}: values must be text")
    return value


def parse_patterns(text: str, path: Path = Path("patterns.yaml")) -> list[dict[str, str]]:
    """Parse the source's ordered list of flat records without a YAML dependency."""
    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None

    for line_number, line in enumerate(text.splitlines(), start=1):
        first = _FIRST_FIELD.match(line)
        if first:
            current = {}
            records.append(current)
            key, raw = first.groups()
        else:
            field = _FIELD.match(line)
            if field and current is not None:
                key, raw = field.groups()
            else:
                raise PatternError(
                    f"{path}:{line_number}: expected `- key: value` or `  key: value`"
                )
        if key in current:
            raise PatternError(f"{path}:{line_number}: `{key}` is declared twice in one entry")
        current[key] = _value(raw, path, line_number)

    if not records:
        raise PatternError(f"{path}: declares no patterns")
    return records


def load_patterns(path: Path) -> list[dict[str, str]]:
    """Load patterns from a source path."""
    return parse_patterns(path.read_text(encoding="utf-8"), path)


def build_floor(patterns: Iterable[dict[str, str]]) -> dict[str, object]:
    """Turn floor-covered patterns and documented gaps into the floor's JSON shape."""
    entries: list[dict[str, str]] = []
    guard_only: list[dict[str, str]] = []
    seen_guard_only: set[tuple[str, str]] = set()

    for index, record in enumerate(patterns, start=1):
        # The host permission floor applies to a whole session and has no representation
        # for a Claude subagent role.  Role additions therefore belong only to guard.py.
        if "agent_type" in record:
            continue
        try:
            rule = record["rule"]
            floor = record["floor"]
        except KeyError as error:
            raise PatternError(f"pattern {index}: declares no `{error.args[0]}`") from None
        if floor == "yes":
            missing = [key for key in ("list", "pattern") if key not in record]
            if missing:
                raise PatternError(f"pattern {index}: floor entry declares no {', '.join(missing)}")
            entries.append({"rule": rule, "list": record["list"], "pattern": record["pattern"]})
        elif floor == "no":
            # A no-floor command pattern without a reason is guard-only coverage (for
            # example the read-only allowlist), not a floor.json guard_only claim.
            if "why" in record:
                key = (rule, record["why"])
                if key not in seen_guard_only:
                    guard_only.append({"rule": rule, "why": record["why"]})
                    seen_guard_only.add(key)
        else:
            raise PatternError(f"pattern {index}: floor must be `yes` or `no`, not `{floor}`")

    return {
        "format": FORMAT,
        "verified_against": VERIFIED_AGAINST,
        "note": NOTE,
        "entries": entries,
        "guard_only": guard_only,
    }


def render_floor(floor: dict[str, object]) -> str:
    """Render the established floor.json layout, including its intentional spacing."""
    lines = [
        "{",
        f'  "format": {json.dumps(floor["format"])},',
        f'  "verified_against": {json.dumps(floor["verified_against"])},',
        f'  "note": {json.dumps(floor["note"])},',
        '  "entries": [',
    ]
    entries = floor["entries"]
    assert isinstance(entries, list)
    previous_rule: str | None = None
    previous_list: str | None = None
    for index, entry in enumerate(entries):
        assert isinstance(entry, dict)
        rule = entry["rule"]
        assert isinstance(rule, str)
        list_name = entry["list"]
        assert isinstance(list_name, str)
        if index and (rule != previous_rule or list_name != previous_list):
            lines.append("")
        suffix = "," if index + 1 < len(entries) else ""
        lines.append(f"    {json.dumps(entry, separators=(', ', ': '))}{suffix}")
        previous_rule = rule
        previous_list = list_name
    lines.extend(["  ],", '  "guard_only": ['])
    guard_only = floor["guard_only"]
    assert isinstance(guard_only, list)
    for index, entry in enumerate(guard_only):
        assert isinstance(entry, dict)
        rendered = json.dumps(entry, indent=2)
        rendered_lines = rendered.splitlines()
        lines.extend(f"    {line}" for line in rendered_lines[:-1])
        suffix = "," if index + 1 < len(guard_only) else ""
        lines.append(f"    {rendered_lines[-1]}{suffix}")
    lines.extend(["  ]", "}"])
    return "\n".join(lines) + "\n"


def default_paths() -> tuple[Path, Path]:
    """Return the source and committed output paths relative to this script."""
    guard_dir = Path(__file__).resolve().parent
    return guard_dir / "patterns.yaml", guard_dir.parent / "floor.json"


def generate_floor(
    patterns_path: Path | None = None, output_path: Path | None = None
) -> str:
    """Generate and write a floor; alternate paths make regeneration checks non-mutating."""
    default_patterns, default_output = default_paths()
    source = patterns_path or default_patterns
    output = output_path or default_output
    rendered = render_floor(build_floor(load_patterns(source)))
    output.write_text(rendered, encoding="utf-8")
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patterns", type=Path, help="pattern source (default: sibling patterns.yaml)")
    parser.add_argument("--output", type=Path, help="output path (default: plugin/control/floor.json)")
    args = parser.parse_args()
    generate_floor(args.patterns, args.output)


if __name__ == "__main__":
    main()
