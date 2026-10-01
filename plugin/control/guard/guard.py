#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Split shell commands conservatively before the guard classifies them.

Pillar 4's guard deliberately understands only top-level ``;``, ``&&``, ``||``, and
``|``.  It uses only the standard library (decision 15): each resulting segment is
tokenized with :mod:`shlex`, while syntax that could conceal another command is residue,
not an allowlist candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatchcase
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Callable

from generate_floor import load_patterns as _load_pattern_records

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import setup as setup_script  # noqa: E402  (a plugin script, reached by path)


SAFETY_SET = "safety"
CommandSegments = list[tuple[str, ...]]
PatternRecords = list[dict[str, str]]
DecideRunner = Callable[..., subprocess.CompletedProcess[str]]

DECIDE_TIMEOUT_SECONDS = 3


@dataclass(frozen=True)
class Classification:
    """The deterministic result of checking command segments against pattern lists."""

    outcome: str
    rule: str | None = None
    pattern: str | None = None
    decision: str | None = None
    probabilities: dict[str, object] | None = None
    reason: str | None = None


def load_patterns(path: Path | None = None) -> PatternRecords:
    """Load and validate default and role-specific records from ``patterns.yaml``.

    ``patterns.yaml`` is deliberately YAML-shaped rather than YAML.  The floor generator
    already owns the standard-library parser for that shared source, so the guard uses the
    same representation instead of introducing a second parser or a YAML dependency.
    Entries without ``agent_type`` belong to the default lists.  An entry with
    ``agent_type`` is an additional restriction for that role and may therefore be only a
    deny or ask entry.
    """
    source = path or Path(__file__).with_name("patterns.yaml")
    patterns = _load_pattern_records(source)
    for index, record in enumerate(patterns, start=1):
        if "agent_type" not in record:
            continue
        if record.get("list") not in ("deny", "ask"):
            raise ValueError(
                f"{source}: entry {index}: an agent_type entry must declare "
                "`list: deny` or `list: ask`"
            )
    return patterns


def classify_segments(
    segments: CommandSegments,
    patterns: PatternRecords,
    agent_type: str | None = None,
    *,
    safety_active: bool = True,
) -> Classification:
    """Classify segments against default lists and, optionally, role additions.

    The default read-only allowlist remains the first check.  After a command reaches
    deny/ask matching, default and role additions are combined by severity: deny wins
    over ask regardless of which list matched first.  A role's deny or ask entry can
    further restrict an otherwise allowed default command, but can never grant
    permission.

    ``safety_active=False`` skips the default list's own classification entirely,
    treating it as an unconditional allow — the project did not choose the `safety` set,
    or never ran setup.  Role additions are not gated by ``safety_active``: they protect
    harness state whenever their role runs, independent of a project's own set choices.
    """
    if not safety_active:
        default = Classification("allow")
    else:
        default_patterns = [record for record in patterns if "agent_type" not in record]
        default = _classify_against_patterns(segments, default_patterns)
    if agent_type is None:
        return default

    role_patterns = [
        record for record in patterns if record.get("agent_type") == agent_type
    ]
    role = _classify_against_patterns(segments, role_patterns)

    # An allowlist match ends default deny/ask matching, as before.  Role additions
    # remain able to add a restriction to that otherwise allowed command.
    if default.outcome == "allow":
        return role if role.outcome in ("deny", "ask") else default

    # A role's addition and the default lists are parallel sources of restrictions.
    # Choose the more severe outcome rather than whichever source was checked first;
    # prefer the role's reason when both sources match at the same severity.
    if role.outcome == "deny":
        return role
    if default.outcome == "deny":
        return default
    if role.outcome == "ask":
        return role
    if default.outcome == "ask":
        return default

    return default


def classify_command(
    command: str,
    patterns: PatternRecords,
    *,
    cwd: str | Path,
    branch: str,
    is_worktree: bool,
    agent_type: str | None = None,
    run_decide: DecideRunner = subprocess.run,
    safety_active: bool = True,
) -> Classification:
    """Classify one command, asking ``guard.risk`` only for deterministic residue.

    ``run_decide`` is a seam for callers' tests; production uses :func:`subprocess.run`.
    The splitter's ambiguous result is residue too, since it must not be silently allowed.
    ``safety_active`` is the caller's own decision (see ``_safety_enabled``), not computed
    here, so a direct caller's existing behaviour is unchanged unless it opts in.
    """
    try:
        segments = split_command(command)
        if segments is not None:
            result = classify_segments(
                segments, patterns, agent_type, safety_active=safety_active
            )
        elif not safety_active:
            result = Classification("allow")
        else:
            result = Classification("residue")
    except Exception as error:
        result = Classification("ask", reason=f"guard internal error ({error})")
        append_journal(
            Path(cwd),
            journal_entry(
                command,
                agent_type,
                result,
                "internal_error",
                message=str(error),
            ),
        )
        return result

    source = "pattern"
    if result.outcome == "residue":
        source = "guard.risk"
        result = classify_residue(
            command,
            cwd=cwd,
            branch=branch,
            is_worktree=is_worktree,
            run_decide=run_decide,
        )

    if result.outcome in ("deny", "ask"):
        append_journal(
            Path(cwd),
            journal_entry(command, agent_type, result, source),
        )
    return result


def classify_residue(
    command: str,
    *,
    cwd: str | Path,
    branch: str,
    is_worktree: bool,
    run_decide: DecideRunner = subprocess.run,
) -> Classification:
    """Map a ``guard.risk`` answer to allow or ask, retrying a failed CLI call once.

    A clean unresolved answer is already an answer from ``decide.py`` and maps straight
    to ask.  Only a failed subprocess contract (including malformed JSON) is retried.
    """
    state = {
        "command": command,
        "cwd": str(cwd),
        "branch": branch,
        "is_worktree": is_worktree,
    }
    argv = [
        sys.executable,
        str(Path(__file__).resolve().parents[2] / "scripts" / "decide.py"),
        "ask",
        "--question",
        "guard.risk",
        "--decisions-dir",
        str(Path(__file__).resolve().parent),
        "--state",
        "-",
    ]

    last_failure: str | None = None
    for _ in range(2):
        try:
            completed = run_decide(
                argv,
                input=json.dumps(state),
                capture_output=True,
                text=True,
                timeout=DECIDE_TIMEOUT_SECONDS,
                cwd=str(cwd),
            )
            if completed.returncode != 0:
                raise RuntimeError(f"decide.py exited {completed.returncode}")
            outcome = json.loads(completed.stdout)
            if not isinstance(outcome, dict) or not isinstance(
                outcome.get("resolved"), bool
            ):
                raise ValueError("decide.py returned an invalid outcome")
            if outcome["resolved"] and not isinstance(outcome.get("decision"), str):
                raise ValueError("decide.py omitted the resolved decision")
        except Exception as error:
            last_failure = str(error)
            continue

        decision = outcome.get("decision") if outcome["resolved"] else None
        probabilities = outcome.get("probabilities")
        if outcome["resolved"] and outcome["decision"] == "read_only":
            return Classification("allow", decision=decision, probabilities=probabilities)
        reason = outcome.get("reason")
        if not outcome["resolved"] and isinstance(reason, str):
            reason = f"guard.risk could not resolve this command ({reason})"
        else:
            reason = None
        return Classification(
            "ask", decision=decision, probabilities=probabilities, reason=reason
        )

    detail = f" ({last_failure})" if last_failure else ""
    return Classification("ask", reason=f"guard.risk backend failure{detail}")


# --- the journal -------------------------------------------------------------------


def journal_path(project: Path) -> Path:
    """Return the guard's journal below the project state directory."""
    return project / ".harnex" / "state" / "guard" / "journal.jsonl"


def journal_entry(
    command: str,
    agent_type: str | None,
    classification: Classification,
    source: str,
    *,
    message: str | None = None,
) -> dict[str, object]:
    """Build the journal record for a deny or ask classification."""
    entry: dict[str, object] = {
        "command": command,
        "agent_type": agent_type,
        "outcome": classification.outcome,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if source == "pattern":
        entry["rule"] = classification.rule
        entry["pattern"] = classification.pattern
    elif source == "internal_error":
        entry["message"] = message
    else:
        entry["decision"] = classification.decision
        entry["probabilities"] = classification.probabilities
    return entry


def append_journal(project: Path, entry: dict[str, object]) -> None:
    """Append one JSON record, creating the guard state directory as needed."""
    path = journal_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def _classify_against_patterns(
    segments: CommandSegments, patterns: PatternRecords
) -> Classification:
    """Classify segments against one allow, deny, then ask pattern set.

    An allow requires every segment to match.  Deny and ask each require only one match.
    Pattern-less records are documentation notes, not permission patterns, and are
    therefore excluded from every list before matching.
    """
    lists = {
        list_name: [
            record
            for record in patterns
            if record.get("list") == list_name and record.get("pattern") is not None
        ]
        for list_name in ("allow", "deny", "ask")
    }

    allowed = [_first_matching_record(segment, lists["allow"]) for segment in segments]
    if allowed and all(allowed):
        record = allowed[0]
        assert record is not None
        return _classification("allow", record)

    for outcome in ("deny", "ask"):
        for record in lists[outcome]:
            if any(_matches_segment(segment, record["pattern"]) for segment in segments):
                return _classification(outcome, record)

    return Classification("residue")


def _first_matching_record(
    segment: tuple[str, ...], records: PatternRecords
) -> dict[str, str] | None:
    """Return the first record whose pattern matches a shell command segment."""
    for record in records:
        if _matches_segment(segment, record["pattern"]):
            return record
    return None


def _classification(outcome: str, record: dict[str, str]) -> Classification:
    """Make a result that retains the pattern and rule responsible for it."""
    return Classification(outcome, record["rule"], record["pattern"])


def _matches_segment(segment: tuple[str, ...], pattern: str) -> bool:
    """Match one Bash segment against the floor's ``Bash(...)`` glob syntax."""
    tool, spec = _split_pattern(pattern)
    return tool == "Bash" and spec is not None and fnmatchcase(" ".join(segment), spec)


def _split_pattern(pattern: str) -> tuple[str, str | None]:
    """Split ``Bash(git push *)`` into its tool and glob specification."""
    if pattern.endswith(")") and "(" in pattern:
        tool, _, spec = pattern.partition("(")
        return tool, spec[:-1]
    return pattern, None


def split_command(command: str) -> CommandSegments | None:
    """Return tokenized top-level command segments, or ``None`` when ambiguous.

    Quotes and shell escapes keep the four recognised operators inside an argument.  A
    malformed segment, command substitution, or another top-level shell control form is
    deliberately ambiguous: later guard stages must send it to the residue path rather
    than attempt deterministic matching.
    """
    segments = _raw_segments(command)
    if segments is None:
        return None

    parsed: CommandSegments = []
    for segment in segments:
        if _has_command_substitution(segment):
            return None
        try:
            tokens = shlex.split(segment, posix=True, comments=False)
        except ValueError:
            return None
        if not tokens:
            return None
        parsed.append(tuple(tokens))
    return parsed


def _raw_segments(command: str) -> list[str] | None:
    """Split only the simple top-level operators, preserving text for ``shlex``."""
    segments: list[str] = []
    quote: str | None = None
    start = 0
    index = 0

    while index < len(command):
        character = command[index]
        if quote:
            if character == "\\" and quote == '"':
                index += 2
                continue
            if character == quote:
                quote = None
            index += 1
            continue

        if character in "'\"":
            quote = character
            index += 1
            continue
        if character == "\\":
            index += 2
            continue
        if character == ";":
            end = index + 1
        elif command.startswith("&&", index) or command.startswith("||", index):
            end = index + 2
        elif character == "|":
            end = index + 1
        elif character in "&()<>\n":
            return None
        else:
            index += 1
            continue

        segment = command[start:index]
        if not segment.strip():
            return None
        segments.append(segment)
        start = end
        index = end

    final = command[start:]
    if not final.strip():
        return None
    segments.append(final)
    return segments


def _has_command_substitution(segment: str) -> bool:
    """Whether a segment has a backtick or a dollar-parenthesis not escaped by ``\\``."""
    if "`" in segment:
        return True

    index = 0
    while True:
        index = segment.find("$(", index)
        if index < 0:
            return False
        escapes = 0
        before = index - 1
        while before >= 0 and segment[before] == "\\":
            escapes += 1
            before -= 1
        if escapes % 2 == 0:
            return True
        index += 2


# --- the hook ----------------------------------------------------------------------


def _resolve_project_root(payload: dict[str, object]) -> Path:
    """Return the project root supplied by the host or its hook payload."""
    root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or "."
    if not isinstance(root, str):
        raise ValueError("the hook payload's cwd is not text")
    return Path(root)


def _git_metadata(cwd: Path) -> tuple[str, bool]:
    """Read the branch and worktree state without making a git failure a hook failure."""

    def git(*arguments: str) -> str | None:
        try:
            completed = subprocess.run(
                ["git", *arguments],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=1,
            )
        except Exception:
            return None
        if completed.returncode != 0:
            return None
        value = completed.stdout.strip()
        return value or None

    branch = git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    git_dir = git("rev-parse", "--git-dir")
    common_dir = git("rev-parse", "--git-common-dir")
    if git_dir is None or common_dir is None:
        return branch, False

    def resolved(path: str) -> Path:
        candidate = Path(path)
        return candidate if candidate.is_absolute() else cwd / candidate

    return branch, resolved(git_dir) != resolved(common_dir)


def _safety_enabled(project: Path) -> bool:
    """Whether the project's own `.harnex.yml` chose the `safety` set.

    Fails safe: a missing `.harnex.yml`, or one that parses but does not list `safety`,
    makes the default list inert (decision 19, mirroring ``canary.py``'s own check for its
    set). Anything else — unreadable or malformed — is treated as enabled, since an error
    is never grounds to allow (the guard's own "never allow on its own error" rule).
    """
    choices_path = project / setup_script.CHOICES
    if not choices_path.is_file():
        return False
    try:
        choices = setup_script.parse_choices(
            choices_path.read_text(encoding="utf-8"), str(choices_path)
        )
    except (OSError, setup_script.SetupError):
        return True
    return SAFETY_SET in choices.get("sets", [])


def _hook_output(classification: Classification, *, failure: str | None = None) -> dict[str, object]:
    """Translate a guard result into Claude Code's PreToolUse output contract."""
    decision = classification.outcome
    output: dict[str, object] = {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
    }
    if decision != "allow":
        if failure is not None:
            reason = failure
        elif classification.rule and classification.pattern:
            reason = (
                f"guard rule `{classification.rule}` matched "
                f"`{classification.pattern}`"
            )
        elif classification.decision:
            reason = f"guard.risk classified this command as `{classification.decision}`"
        elif classification.reason:
            reason = classification.reason
        else:
            reason = "guard.risk did not resolve this command; permission is required"
        output["permissionDecisionReason"] = reason
    return {"hookSpecificOutput": output}


def _classify_hook_payload(raw: str) -> Classification:
    """Read a Bash hook payload and classify its command."""
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("the hook input is not a JSON object")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        raise ValueError("the hook input has no tool_input object")
    command = tool_input.get("command")
    if not isinstance(command, str) or not command:
        raise ValueError("the hook input has no tool_input.command")
    agent_type = payload.get("agent_type")
    if agent_type is not None and not isinstance(agent_type, str):
        raise ValueError("the hook input's agent_type is not text")

    cwd = _resolve_project_root(payload)
    branch, is_worktree = _git_metadata(cwd)
    return classify_command(
        command,
        load_patterns(),
        cwd=cwd,
        branch=branch,
        is_worktree=is_worktree,
        agent_type=agent_type,
        safety_active=_safety_enabled(cwd),
    )


def main() -> int:
    """Run as a PreToolUse hook: always emit valid JSON and always exit successfully."""
    try:
        output = _hook_output(_classify_hook_payload(sys.stdin.read()))
    except json.JSONDecodeError as error:
        output = _hook_output(
            Classification("ask"),
            failure=f"the hook input is not readable JSON ({error})",
        )
    except Exception as error:
        output = _hook_output(
            Classification("ask"),
            failure=f"the guard could not classify this command ({error})",
        )
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
