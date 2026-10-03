#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Refresh a harnessed project's harness-owned content, without asking a question.

Pillar 2's update script. Unlike `setup.py`, no session is asking questions on its
behalf, so it reads the project's own recorded choices — `.harnex.yml` — itself,
rather than being handed an answers document assembled by hand (design.md D2).

No dependency outside the standard library, for the same reason `setup.py` carries
none: a harness script paying for a dependency resolution before its first write is
exactly what decision 15 rules out.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import setup  # noqa: E402  (a sibling script, reached the way setup reaches render_rules)

# --- reading the project's own recorded choices --------------------------------------


def read_choices(text: str, plugin_root: Path, path: str = setup.CHOICES) -> "setup.Answers":
    """Read `.harnex.yml`'s own flat shape into the `Answers` `validate_answers` checks.

    No session is assembling an answers document for update the way one does for setup,
    so there are no approvals to read: every approval flag is `False` and `adopt` is
    empty, which already routes `build_plan` to never insert a pointer line or adopt a
    conflict on update's behalf (design.md D1). Parsing itself is `setup.parse_choices`,
    unchanged — the reader is the schema, and the schema is stated once.
    """
    values = setup.parse_choices(text, path)
    answers = setup.Answers(
        project_name=str(values["project_name"]),
        profiles=tuple(values["profiles"]),  # type: ignore[arg-type]
        sets=tuple(values["sets"]),  # type: ignore[arg-type]
        features=tuple(values["features"]),  # type: ignore[arg-type]
        canary=str(values["canary"]),
        decision_model=str(values["decision_model"]),
        check_command=str(values["check_command"]),
    )
    setup.validate_answers(answers, plugin_root)
    return answers


def read_local_choices(text: str, plugin_root: Path, path: str = setup.LOCAL_CHOICES) -> "setup.Answers":
    """`read_choices`'s own local-visibility twin (docs/PLAN.md C7): `.harnex/config.yml`'s
    ten-key shape, same no-approvals reasoning, same `setup.parse_choices` reader — just
    the other key/list-key set."""
    values = setup.parse_choices(text, path, setup.LOCAL_ANSWER_KEYS, setup.LOCAL_LIST_KEYS)
    answers = setup.Answers(
        project_name=str(values["project_name"]),
        profiles=tuple(values["profiles"]),  # type: ignore[arg-type]
        sets=tuple(values["sets"]),  # type: ignore[arg-type]
        features=tuple(values["features"]),  # type: ignore[arg-type]
        canary=str(values["canary"]),
        decision_model=str(values["decision_model"]),
        check_command=str(values["check_command"]),
        visibility=str(values["visibility"]),
        tools=tuple(values["tools"]),  # type: ignore[arg-type]
        store_id=str(values["store_id"]),
    )
    setup.validate_answers(answers, plugin_root)
    return answers


def read_recorded_choices(project: Path, plugin_root: Path) -> "setup.Answers":
    """Whichever file is there — `.harnex/config.yml` (local) or `.harnex.yml` (shared) —
    read into the same `Answers` shape (local-visibility spec's own "every harness
    operation reads this value... rather than infer it", satisfied by which file exists,
    design.md D2). Raises the same refusal `run_update` already raised for a missing
    `.harnex.yml`, now naming whichever path is actually missing."""
    local_path = project / setup.LOCAL_CHOICES
    if local_path.is_file():
        return read_local_choices(local_path.read_text(encoding="utf-8"), plugin_root)
    shared_path = project / setup.CHOICES
    if shared_path.is_file():
        return read_choices(shared_path.read_text(encoding="utf-8"), plugin_root)
    raise setup.SetupError(
        f"neither {setup.LOCAL_CHOICES} nor {setup.CHOICES} is here, so this project has "
        "not been set up. Run `/harnex:setup` instead."
    )


# --- update's own run: plan and write in one pass, no approval gate (design.md D3) --


def run_update(project: Path, plugin_root: Path, home: Path | None = None) -> tuple[str, bool]:
    """Refresh a project's harness-owned content from its own recorded choices.

    Raises `setup.SetupError`, writing nothing, for either refusal: neither recorded
    answers file present (the project was never set up), or present with no manifest
    (there is no record of what the harness owns, so update will not guess — setup can
    adopt it).

    Otherwise builds the plan through `setup.build_plan(..., mode="update")` and, since
    an update plan holds nothing beyond what setup's own yes already approved (design.md
    D3), either stops on a conflict the same way setup's own CLI does, writing nothing,
    or applies it in the same pass. Returns the report `setup.render_plan` already knows
    how to produce, and whether the run succeeded (`False` for a conflict).
    """
    answers = read_recorded_choices(project, plugin_root)

    if setup.read_manifest(project) is None:
        raise setup.SetupError(
            f"{setup.MANIFEST} is not here, so there is no record of what the harness "
            "owns in this project; update will not guess at it. Run `/harnex:setup`, "
            "which can adopt the project, instead."
        )

    plan = setup.build_plan(project, plugin_root, answers, mode="update", home=home)
    if plan.conflicts:
        return setup.render_plan(plan, verb="plan"), False

    written = setup.apply_plan(plan)
    report = setup.render_plan(plan, verb="write")
    if written:
        report += "Written: " + ", ".join(written) + "\n"
    return report, True


# --- the command line -----------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Refresh a harnessed project's harness-owned content from its own recorded "
            "choices, planning and writing in one pass."
        )
    )
    parser.add_argument("--project", default=".", help="the project to update")
    parser.add_argument("--plugin-root", default=None, help="where the harness is installed")
    parser.add_argument(
        "--home", default=None, help="the home directory (local visibility's one global offer)"
    )
    args = parser.parse_args(argv)

    project = Path(args.project).resolve()
    plugin_root = (
        Path(args.plugin_root).resolve() if args.plugin_root else setup.default_plugin_root()
    )
    home = Path(args.home).resolve() if args.home else None

    try:
        report, ok = run_update(project, plugin_root, home)
    except setup.SetupError as error:
        print(f"update: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"update: {error}", file=sys.stderr)
        return 1

    print(report, end="")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
