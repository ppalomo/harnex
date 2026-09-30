#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""`apply`'s own deterministic steps: run state, fingerprinting, routing, scope checks,
acceptance, and ticking — everything `docs/PLAN.md` §10 fixes that does not require
starting a builder. Starting one (a Codex job through its own plugin's slash commands, or
a Claude fallback subagent through the `Agent` tool) is not something a script can do —
those are session-level actions the `/harnex:apply` skill takes, calling into this module
between them, the same "scripts never talk to the person" split C1c and C2 already use.

    uv run plugin/scripts/apply_loop.py route --project <root> --change <name>
    uv run plugin/scripts/apply_loop.py scope --project <root> --task-id <id> \\
        --task-text <text> --before <file> --after <file>
    uv run plugin/scripts/apply_loop.py fingerprint --project <root> --base <ref>
    uv run plugin/scripts/apply_loop.py check --project <root> --task-id <id> \\
        --paths <newline-joined> --before <file> --after <file>
    uv run plugin/scripts/apply_loop.py tick --project <root> --change <name> --task-id <id>
    uv run plugin/scripts/apply_loop.py state show|transition ...

Standard library only, importing `decide.py` and `task_scope_check.py` directly as
sibling modules in `scripts/` and `feedback/` respectively.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "feedback"))
import decide  # noqa: E402  (a plugin script, reached by path)
import task_scope_check  # noqa: E402  (a plugin script, reached by path)
from working_tree import tree_fingerprint  # noqa: E402  (a plugin script, reached by path)

TASK_LINE = re.compile(r"^(?P<indent>\s*)- \[(?P<mark>[ xX])\] (?P<id>\S+) (?P<text>.*)$")
PATH_SPAN = re.compile(r"`([^`\s]+/[^`\s]+)`")

TRANSITIONS = ("queued", "delegated", "returned", "checked", "accepted", "escalated")


class ApplyLoopError(Exception):
    """A task list, a run state, or a request this module cannot honour."""


# --- reading tasks.md ------------------------------------------------------------------


@dataclass(frozen=True)
class Task:
    id: str
    text: str
    done: bool
    paths: tuple[str, ...]


def extract_declared_paths(text: str) -> tuple[str, ...]:
    """Every backtick-quoted span in a task's own text that looks like a path — a `/`,
    no whitespace, not a URL. This is how every task in this repository's own `tasks.md`
    files already names its target files; no new authoring convention is needed."""
    spans = PATH_SPAN.findall(text)
    return tuple(dict.fromkeys(span for span in spans if not span.startswith("http")))


def parse_tasks(text: str) -> list[Task]:
    tasks = []
    for line in text.splitlines():
        match = TASK_LINE.match(line)
        if not match:
            continue
        task_text = match.group("text")
        tasks.append(
            Task(
                id=match.group("id"),
                text=task_text,
                done=match.group("mark").lower() == "x",
                paths=extract_declared_paths(task_text),
            )
        )
    return tasks


def tasks_md_path(project: Path, change: str) -> Path:
    return project / "openspec" / "changes" / change / "tasks.md"


def load_tasks(project: Path, change: str) -> list[Task]:
    return parse_tasks(tasks_md_path(project, change).read_text(encoding="utf-8"))


def tick_task(project: Path, change: str, task_id: str) -> None:
    """The loop's own act (`apply-command`'s own requirement) — never the builder's."""
    path = tasks_md_path(project, change)
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"^(?P<indent>\s*)- \[ \] {re.escape(task_id)}(?=\s)", re.MULTILINE
    )
    new_text, count = pattern.subn(r"\g<indent>- [x] " + task_id, text)
    if count == 0:
        raise ApplyLoopError(f"no unticked task `{task_id}` in {path}")
    if count > 1:
        raise ApplyLoopError(f"task id `{task_id}` is ambiguous in {path}")
    path.write_text(new_text, encoding="utf-8")


# --- fingerprinting ----------------------------------------------------------------------


def current_head(project: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(project), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


# --- routing: task.route, batched across every queued task -----------------------------


def _route_question_for(template: decide.Question, index: int, task: Task) -> decide.Question:
    """One question per task, its own id and self-contained `instructions` — never a
    shared `state` scoped per item, a shape the Decisions API's own docs do not confirm
    (design.md D2)."""
    paths_text = ", ".join(task.paths) if task.paths else "(none declared)"
    instructions = (
        f"{template.instructions}\n\n"
        f"Task {task.id}: {task.text}\n"
        f"Declared paths: {paths_text}"
    )
    return decide.Question(
        id=f"task.route#{index}",
        type=template.type,
        state_fields=(),
        options=template.options,
        rule_threshold=template.rule_threshold,
        rule_threshold_low=None,
        instructions=instructions,
        path=template.path,
    )


def format_route_line(task_id: str, outcome: dict[str, object]) -> str:
    if outcome["resolved"]:
        return f"Decision: apply({task_id}) → {outcome['decision']} · confidence {outcome['confidence']}"
    return f"Decision: apply({task_id}) → ask ({outcome['reason']})"


def route_all(
    project: Path,
    decisions_dir: Path,
    tasks: list[Task],
    backend: str,
    api_key: str | None,
) -> list[dict[str, object]]:
    """`task.route`, once per queued task, in one `decide_many` call. Returns one entry
    per task: `{"task_id", "line", "outcome"}`."""
    template = decide.load_question("task.route", decisions_dir)
    items = [(_route_question_for(template, index, task), {}) for index, task in enumerate(tasks)]
    outcomes = decide.decide_many(items, backend, api_key=api_key)

    results = []
    for task, (question, state), outcome in zip(tasks, items, outcomes):
        decide.append_journal(project, decide.journal_entry(question, state, outcome))
        results.append({"task_id": task.id, "line": format_route_line(task.id, outcome), "outcome": outcome})
    return results


# --- task.scope: one call, after a paths-less task's builder has written ----------------


def ask_scope(
    project: Path,
    decisions_dir: Path,
    task: Task,
    changed_paths_text: str,
    backend: str,
    api_key: str | None,
) -> dict[str, object]:
    question = decide.load_question("task.scope", decisions_dir)
    state = {"task_text": task.text, "changed_paths": changed_paths_text}
    outcome = decide.decide(question, state, backend, api_key=api_key)
    decide.append_journal(project, decide.journal_entry(question, state, outcome))
    return outcome


# --- acceptance: a conjunction of facts, never a judgement ------------------------------


@dataclass(frozen=True)
class Acceptance:
    accepted: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)


def evaluate_acceptance(
    *,
    builder_reported_done: bool,
    check_exit_code: int,
    declared_violations: list[str],
    protected_violations: list[str],
    scope_outcome: dict[str, object] | None,
    head_moved: bool,
    fingerprint_at_check: str,
    fingerprint_at_acceptance: str,
) -> Acceptance:
    reasons: list[str] = []
    if not builder_reported_done:
        reasons.append("the builder did not report the task done")
    if check_exit_code != 0:
        reasons.append(f"the check exited {check_exit_code}")
    if declared_violations:
        reasons.append(f"outside the task's declared paths: {', '.join(declared_violations)}")
    if protected_violations:
        reasons.append(f"a protected path was touched: {', '.join(protected_violations)}")
    if scope_outcome is not None:
        if not scope_outcome.get("resolved"):
            reasons.append("task.scope did not resolve")
        elif scope_outcome.get("decision") != "true":
            reasons.append("task.scope judged the write out of scope")
    if head_moved:
        reasons.append("HEAD or a ref moved during the run")
    if fingerprint_at_check != fingerprint_at_acceptance:
        reasons.append("the working tree changed since the check ran")
    return Acceptance(accepted=not reasons, reasons=tuple(reasons))


# --- run state: .harnex/state/apply/<change>.json, one entry per task ------------------


def run_state_path(project: Path, change: str) -> Path:
    return project / ".harnex" / "state" / "apply" / f"{change}.json"


def load_run_state(project: Path, change: str) -> dict[str, object]:
    path = run_state_path(project, change)
    if not path.is_file():
        return {"change": change, "tasks": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_run_state(project: Path, change: str, state: dict[str, object]) -> None:
    """Atomic: write to a temp file beside the target, then rename — never a
    half-written state file, whatever crashes mid-write."""
    path = run_state_path(project, change)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp_path, path)


def resume_action(entry: dict[str, object] | None) -> str:
    """What a resumed run does with one task's recorded entry — pure classification,
    the recovery contract's own decision table (`docs/PLAN.md` §10, S1's staleness
    finding). The Codex job-status lookup and the keep/discard/re-delegate question
    themselves are session-level actions the skill takes; this only says which branch
    applies."""
    if entry is None:
        return "start-fresh"
    status = entry.get("status")
    if status == "accepted":
        return "skip"
    if status == "delegated":
        return "lookup-job"
    if status in ("returned", "checked"):
        return "resume-check"
    return "start-fresh"


def transition(
    state: dict[str, object],
    task_id: str,
    status: str,
    **fields: object,
) -> dict[str, object]:
    if status not in TRANSITIONS:
        raise ApplyLoopError(f"`{status}` is not one of {', '.join(TRANSITIONS)}")
    tasks = state.setdefault("tasks", {})
    entry = tasks.setdefault(task_id, {})
    entry["status"] = status
    entry.update(fields)
    return state


# --- the command line --------------------------------------------------------------------


def _read_text_arg(value: str) -> str:
    return sys.stdin.read() if value == "-" else Path(value).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="apply's own deterministic loop steps.")
    parser.add_argument(
        "verb",
        choices=("route", "scope", "fingerprint", "check", "accept", "tick", "state-show", "state-transition"),
    )
    parser.add_argument("--project", default=".")
    parser.add_argument("--change")
    parser.add_argument("--task-id")
    parser.add_argument("--task-text")
    parser.add_argument("--base")
    parser.add_argument("--before")
    parser.add_argument("--after")
    parser.add_argument("--paths", default="")
    parser.add_argument("--status")
    parser.add_argument("--data", default=None, help="a JSON object of extra fields for state-transition")
    parser.add_argument("--builder-done", choices=("true", "false"))
    parser.add_argument("--check-exit-code", type=int)
    parser.add_argument("--check-result", help="path to a `check` verb's JSON output")
    parser.add_argument("--scope-result", help="path to a `scope` verb's JSON output, if the task declared no paths")
    parser.add_argument("--head-before")
    parser.add_argument("--head-after")
    parser.add_argument("--fingerprint-at-check")
    parser.add_argument("--fingerprint-at-acceptance")
    parser.add_argument("--decisions-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    project = Path(args.project).resolve()
    decisions_dir = args.decisions_dir or decide.default_decisions_dir()

    try:
        if args.verb == "route":
            tasks = [task for task in load_tasks(project, args.change) if not task.done]
            backend = decide._project_backend(project)  # noqa: SLF001 (sibling module)
            api_key = os.environ.get("OPENROUTER_API_KEY")
            results = route_all(project, decisions_dir, tasks, backend, api_key)
            for result in results:
                print(result["line"])
            print(json.dumps(results))
        elif args.verb == "scope":
            tasks = {task.id: task for task in load_tasks(project, args.change)}
            task = tasks.get(args.task_id) or Task(args.task_id, args.task_text or "", False, ())
            backend = decide._project_backend(project)  # noqa: SLF001
            api_key = os.environ.get("OPENROUTER_API_KEY")
            changed_paths_text = _read_text_arg(args.after) if args.after else ""
            outcome = ask_scope(project, decisions_dir, task, changed_paths_text, backend, api_key)
            print(json.dumps(outcome))
        elif args.verb == "fingerprint":
            print(json.dumps({"fingerprint": tree_fingerprint(project, args.base)}))
        elif args.verb == "check":
            before_text = _read_text_arg(args.before)
            after_text = _read_text_arg(args.after)
            declared_paths = [line for line in args.paths.splitlines() if line.strip()]
            result = {
                "declared_violations": task_scope_check.check_declared(declared_paths, before_text, after_text)
                if declared_paths
                else [],
                "protected_violations": task_scope_check.check_protected(before_text, after_text),
            }
            print(json.dumps(result))
        elif args.verb == "accept":
            check_result = json.loads(Path(args.check_result).read_text(encoding="utf-8")) if args.check_result else {"declared_violations": [], "protected_violations": []}
            scope_outcome = json.loads(Path(args.scope_result).read_text(encoding="utf-8")) if args.scope_result else None
            result = evaluate_acceptance(
                builder_reported_done=args.builder_done == "true",
                check_exit_code=args.check_exit_code,
                declared_violations=check_result["declared_violations"],
                protected_violations=check_result["protected_violations"],
                scope_outcome=scope_outcome,
                head_moved=args.head_before != args.head_after,
                fingerprint_at_check=args.fingerprint_at_check,
                fingerprint_at_acceptance=args.fingerprint_at_acceptance,
            )
            print(json.dumps({"accepted": result.accepted, "reasons": list(result.reasons)}))
        elif args.verb == "tick":
            tick_task(project, args.change, args.task_id)
            print(f"ticked {args.task_id}")
        elif args.verb == "state-show":
            print(json.dumps(load_run_state(project, args.change)))
        elif args.verb == "state-transition":
            extra_fields = json.loads(args.data) if args.data else {}
            state = load_run_state(project, args.change)
            transition(state, args.task_id, args.status, **extra_fields)
            save_run_state(project, args.change, state)
            print(json.dumps(state))
    except (ApplyLoopError, decide.DecisionError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"apply-loop: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
