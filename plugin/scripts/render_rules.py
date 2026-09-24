#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Render a project's rules file from the rule sets it chose.

Pillar 1's only script. It reads the rule files under ``context/rules/``, keeps the ones
the project asked for, and writes them out as one document. The output is a pure function
of the chosen sets and profiles: no timestamp, no version, no dependence on the order the
sets were given. That is what lets ``update`` own the rendered file by hash.

    uv run plugin/scripts/render_rules.py --sets git,code --out -

No dependency outside the standard library, deliberately: setup and, later, hooks with a
few seconds to live call this code, and resolving a dependency first is the difference
between instant and not.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# The kinds of enforcement a rule may declare. What each one means, and which pillar it
# lives in, is stated in context/rules/README.md.
ENFORCEMENT_KINDS = frozenset({"none", "guard", "hook", "check", "decision"})

FRONTMATTER_FIELDS = frozenset({"id", "set", "applies_to", "enforced_by"})

ALWAYS = "always"

_DELIMITER = "---"
_FIELD = re.compile(r"^([a-z][a-z_]*): *(\S.*?) *$")
_HEADING = re.compile(r"^(#+) +(\S.*?) *$")

HEADER = """\
# Rules

These are the rules every agent working in this project follows. They come from the
harness, from the rule sets this project chose. Nothing here is specific to this
project; anything that is belongs in the project's own working instructions.

Generated file — do not edit it by hand. It is rendered from the sets recorded in
`.harnex.yml`, and `update` will stop rather than overwrite a file that was edited
after it was written. To change which rules apply, change the sets. To change a rule,
change it in the harness.

Sets in this file: {sets}."""


class RuleError(ValueError):
    """A rule file, or a request to render one, that cannot be understood."""


@dataclass(frozen=True)
class Rule:
    """One rule: what it is, where it lives, and the prose an agent reads."""

    id: str
    set: str
    applies_to: str
    enforced_by: str
    statement: str
    reason: str
    path: Path


def parse_frontmatter(text: str, path: Path) -> tuple[dict[str, str], str]:
    """Split a rule file into its four fields and its body.

    The format is `key: value` scalars and nothing else — no nesting, no lists, no
    quoting, no multi-line values. Anything else is refused rather than guessed at, so
    that the format is its own schema.
    """
    lines = text.split("\n")
    if not lines or lines[0].rstrip() != _DELIMITER:
        raise RuleError(f"{path}: does not open with a `{_DELIMITER}` frontmatter block")

    try:
        end = lines.index(_DELIMITER, 1)
    except ValueError:
        raise RuleError(f"{path}: the frontmatter block is never closed") from None

    fields: dict[str, str] = {}
    for offset, line in enumerate(lines[1:end], start=2):
        if not line.strip():
            raise RuleError(f"{path}:{offset}: blank line inside the frontmatter")
        match = _FIELD.match(line)
        if not match:
            raise RuleError(
                f"{path}:{offset}: {line!r} is not `key: value`. Rule frontmatter holds "
                "four plain string fields; nesting, lists and quoting are not read."
            )
        key, value = match.group(1), match.group(2)
        if value[0] in "[{|>'\"&*":
            raise RuleError(
                f"{path}:{offset}: {value!r} is not a plain string value. Rule "
                "frontmatter holds four plain string fields."
            )
        if key in fields:
            raise RuleError(f"{path}:{offset}: `{key}` is declared twice")
        fields[key] = value

    return fields, "\n".join(lines[end + 1 :])


def parse_rule(path: Path, expected_set: str) -> Rule:
    """Read one rule file, refusing anything the renderer could not render faithfully."""
    fields, body = parse_frontmatter(path.read_text(encoding="utf-8"), path)

    missing = sorted(FRONTMATTER_FIELDS - set(fields))
    if missing:
        raise RuleError(f"{path}: declares no {', '.join(missing)}")
    unknown = sorted(set(fields) - FRONTMATTER_FIELDS)
    if unknown:
        raise RuleError(
            f"{path}: declares {', '.join(unknown)}, which the format does not hold. "
            f"The fields are {', '.join(sorted(FRONTMATTER_FIELDS))}."
        )

    if fields["id"] != path.stem:
        raise RuleError(f"{path}: declares id `{fields['id']}` but is named `{path.stem}`")
    if fields["set"] != expected_set:
        raise RuleError(
            f"{path}: declares set `{fields['set']}` but is stored in `{expected_set}`"
        )
    if fields["enforced_by"] not in ENFORCEMENT_KINDS:
        raise RuleError(
            f"{path}: enforced_by `{fields['enforced_by']}` is not one of "
            f"{', '.join(sorted(ENFORCEMENT_KINDS))}"
        )

    statement, reason = _split_body(body, path)
    return Rule(
        id=fields["id"],
        set=fields["set"],
        applies_to=fields["applies_to"],
        enforced_by=fields["enforced_by"],
        statement=statement,
        reason=reason,
        path=path,
    )


def _split_body(body: str, path: Path) -> tuple[str, str]:
    """The body opens with the rule as one sentence; the rest is why it exists."""
    lines = body.split("\n")
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first is None:
        raise RuleError(f"{path}: states no rule")

    heading = _HEADING.match(lines[first])
    if not heading or heading.group(1) != "#":
        raise RuleError(
            f"{path}: the body must open with `# ` and the rule stated as one sentence"
        )

    rest = lines[first + 1 :]
    for offset, line in enumerate(rest, start=first + 2):
        if _HEADING.match(line):
            raise RuleError(
                f"{path}:{offset}: a second heading. One file states one rule; a body "
                "that needs a second heading is two rules."
            )

    reason = "\n".join(rest).strip()
    if not reason:
        raise RuleError(f"{path}: states the rule but gives no reason for it")
    return heading.group(2), reason


def default_rules_dir() -> Path:
    """Where the rules live relative to this script, installed or in a checkout."""
    return Path(__file__).resolve().parent.parent / "context" / "rules"


def load_sets(rules_dir: Path) -> dict[str, list[Rule]]:
    """Every set the harness holds, each with its rules, read from the tree itself.

    Sets are the directories; there is no list to keep in step with them.
    """
    if not rules_dir.is_dir():
        raise RuleError(f"{rules_dir} is not a directory of rule sets")

    sets: dict[str, list[Rule]] = {}
    seen: dict[str, Path] = {}
    for directory in sorted(p for p in rules_dir.iterdir() if p.is_dir()):
        rules = []
        for path in sorted(directory.glob("*.md")):
            rule = parse_rule(path, directory.name)
            if rule.id in seen:
                raise RuleError(
                    f"{path}: id `{rule.id}` is already used by {seen[rule.id]}. "
                    "A rule is stated once."
                )
            seen[rule.id] = path
            rules.append(rule)
        sets[directory.name] = rules
    return sets


def available_sets(rules_dir: Path | None = None) -> list[str]:
    """The sets a project may choose, in the order they are rendered."""
    return sorted(load_sets(rules_dir or default_rules_dir()))


def render(
    chosen: list[str],
    profiles: list[str] | None = None,
    rules_dir: Path | None = None,
) -> str:
    """Render the chosen sets into the document a project reads.

    Sets come out alphabetically and rules alphabetically within their set, so the
    result depends on which sets were chosen and never on how they were asked for.
    """
    sets = load_sets(rules_dir or default_rules_dir())
    wanted = sorted(set(chosen))
    if not wanted:
        raise RuleError("no set was chosen. " + _holdings(sets))
    unknown = sorted(set(wanted) - set(sets))
    if unknown:
        raise RuleError(f"no such set: {', '.join(unknown)}. " + _holdings(sets))

    allowed = set(profiles or ())
    parts = [HEADER.format(sets=", ".join(wanted))]
    for name in wanted:
        parts.append(f"## {name}")
        for rule in sorted(sets[name], key=lambda r: r.id):
            if rule.applies_to != ALWAYS and rule.applies_to not in allowed:
                continue
            parts.append(f"### {rule.statement}")
            parts.append(rule.reason)
    return "\n\n".join(parts) + "\n"


def _holdings(sets: dict[str, list[Rule]]) -> str:
    return f"The sets held are: {', '.join(sorted(sets))}."


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render a project's rules file from the rule sets it chose.",
    )
    parser.add_argument(
        "--sets", required=True, type=_csv, help="the sets to render, comma separated"
    )
    parser.add_argument(
        "--profiles",
        type=_csv,
        default=[],
        help="the project's profiles, comma separated; rules that apply only to a "
        "profile are rendered when it is listed",
    )
    parser.add_argument(
        "--out",
        default="-",
        help="where to write; `-` is the screen",
    )
    parser.add_argument(
        "--rules-dir",
        type=Path,
        default=None,
        help="read the rules from here instead of from beside this script",
    )
    args = parser.parse_args(argv)

    try:
        document = render(args.sets, args.profiles, args.rules_dir)
    except RuleError as error:
        print(f"render_rules: {error}", file=sys.stderr)
        return 2

    if args.out == "-":
        sys.stdout.write(document)
    else:
        Path(args.out).write_text(document, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
