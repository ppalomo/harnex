#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Answer one typed decision question, through a real backend or by asking the person.

Pillar 3's decision client. One question, one call:

    uv run plugin/scripts/decide.py ask --question phase.route --state state.json \\
        --project <project root>

Prints exactly one JSON object to stdout and exits 0. Every path that is not a clean,
above-threshold `jev` answer — no key, unreachable, a malformed response, below the
question's own threshold, or the project's own backend genuinely being `mock` — collapses
to the same shape: `resolved: false`, with a `prompt` the caller puts to the person. This
script never talks to the person itself and never raises that shape to its caller; asking
is a value it returns, not a side effect it performs.

No dependency outside the standard library (decision 15): the question files under
`../orchestration/decisions/` are YAML-*shaped*, not YAML, parsed the same way a rule's
frontmatter is.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import setup as setup_script  # noqa: E402  (a plugin script, reached by path)

ENDPOINT = "https://openrouter.ai/api/alpha/decisions"
MODEL_ID = "typesafe/jev-1.13"
TOTAL_BUDGET_SECONDS = 3.0
RETRIABLE_STATUSES = frozenset({500, 502, 503, 524, 529})
BACKENDS = frozenset({"mock", "jev"})
QUESTION_TYPES = frozenset({"choice", "noul", "score"})
REQUIRED_QUESTION_FIELDS = frozenset({"id", "type", "state_fields"})
OPTIONAL_QUESTION_FIELDS = frozenset({"rule_threshold", "rule_threshold_low"})
QUESTION_FIELDS = REQUIRED_QUESTION_FIELDS | OPTIONAL_QUESTION_FIELDS
NOUL_OPTIONS = frozenset({"true", "false"})

_DELIMITER = "---"
_FIELD = re.compile(r"^([a-z][a-z_.\-]*): *(\S.*?) *$")
_HEADING = re.compile(r"^(#+) +(\S.*?) *$")


class DecisionError(Exception):
    """A question file, a state, or a request that cannot be understood."""


@dataclass(frozen=True)
class Question:
    """One typed question, as its file declares it."""

    id: str
    type: str
    state_fields: tuple[str, ...]
    options: dict[str, str]
    rule_threshold: float | None
    rule_threshold_low: float | None
    instructions: str
    path: Path
    option_thresholds: dict[str, float] = field(default_factory=dict)


# --- reading a question file ---------------------------------------------------------


def parse_question(text: str, path: Path) -> Question:
    """The format is flat `key: value` fields, a bare `---`, then a prose body — one
    delimiter, not a rule's two, since there is nothing before the fields to close off.
    Two conventions beyond a rule's: `option.<name>` and
    `rule_threshold.<option-name>` keys collect into maps instead of staying literal.
    Nothing else nests."""
    lines = text.split("\n")
    try:
        end = lines.index(_DELIMITER)
    except ValueError:
        raise DecisionError(f"{path}: has no bare `{_DELIMITER}` line separating its fields from its body") from None

    fields: dict[str, str] = {}
    options: dict[str, str] = {}
    option_threshold_values: dict[str, str] = {}
    for offset, line in enumerate(lines[:end], start=1):
        if not line.strip():
            raise DecisionError(f"{path}:{offset}: blank line inside the frontmatter")
        match = _FIELD.match(line)
        if not match:
            raise DecisionError(f"{path}:{offset}: {line!r} is not `key: value`")
        key, value = match.group(1), match.group(2)
        if key.startswith("option."):
            name = key[len("option.") :]
            if not name:
                raise DecisionError(f"{path}:{offset}: `option.` names no option")
            if name in options:
                raise DecisionError(f"{path}:{offset}: option `{name}` is declared twice")
            options[name] = value
            continue
        if key.startswith("rule_threshold."):
            name = key[len("rule_threshold.") :]
            if not name:
                raise DecisionError(f"{path}:{offset}: `rule_threshold.` names no option")
            if name in option_threshold_values:
                raise DecisionError(
                    f"{path}:{offset}: rule threshold for option `{name}` is declared twice"
                )
            option_threshold_values[name] = value
            continue
        if key in fields:
            raise DecisionError(f"{path}:{offset}: `{key}` is declared twice")
        fields[key] = value

    missing = sorted(REQUIRED_QUESTION_FIELDS - set(fields))
    if missing:
        raise DecisionError(f"{path}: declares no {', '.join(missing)}")
    unknown = sorted(set(fields) - QUESTION_FIELDS)
    if unknown:
        raise DecisionError(
            f"{path}: declares {', '.join(unknown)}, which the format does not hold"
        )

    if fields["id"] != path.stem.replace("-", "."):
        raise DecisionError(
            f"{path}: declares id `{fields['id']}` but is named `{path.stem}`"
        )
    if fields["type"] not in QUESTION_TYPES:
        raise DecisionError(
            f"{path}: type `{fields['type']}` is not one of {', '.join(sorted(QUESTION_TYPES))}"
        )
    if fields["type"] == "choice" and not options:
        raise DecisionError(f"{path}: a choice question declares no `option.*`")
    if fields["type"] == "noul" and set(options) != NOUL_OPTIONS:
        raise DecisionError(
            f"{path}: a noul question must declare exactly `option.true` and "
            f"`option.false`, not {sorted(options) or 'none'}"
        )

    threshold: float | None = None
    if fields["type"] == "score":
        if "rule_threshold" in fields:
            raise DecisionError(
                f"{path}: a score question may not declare rule_threshold"
            )
        if "rule_threshold_low" in fields:
            raise DecisionError(
                f"{path}: a score question may not declare rule_threshold_low"
            )
        if not option_threshold_values:
            raise DecisionError(
                f"{path}: a score question declares no `rule_threshold.<option-name>`"
            )
    else:
        if "rule_threshold" not in fields:
            raise DecisionError(
                f"{path}: declares no rule_threshold, required for a {fields['type']} question"
            )
        try:
            threshold = float(fields["rule_threshold"])
        except ValueError:
            raise DecisionError(
                f"{path}: rule_threshold `{fields['rule_threshold']}` is not a number"
            ) from None
        if not 0.0 <= threshold <= 1.0:
            raise DecisionError(f"{path}: rule_threshold must be between 0 and 1")

    threshold_low: float | None = None
    if fields["type"] == "noul":
        if "rule_threshold_low" not in fields:
            raise DecisionError(
                f"{path}: declares no rule_threshold_low, required for a noul question"
            )
        try:
            threshold_low = float(fields["rule_threshold_low"])
        except ValueError:
            raise DecisionError(
                f"{path}: rule_threshold_low `{fields['rule_threshold_low']}` is not a number"
            ) from None
        if not 0.0 <= threshold_low <= 1.0:
            raise DecisionError(f"{path}: rule_threshold_low must be between 0 and 1")
        if threshold_low >= threshold:
            raise DecisionError(
                f"{path}: rule_threshold_low must be below rule_threshold"
            )
    elif "rule_threshold_low" in fields:
        raise DecisionError(
            f"{path}: declares rule_threshold_low, which only a noul question may declare"
        )

    option_thresholds: dict[str, float] = {}
    for name, value in option_threshold_values.items():
        try:
            option_thresholds[name] = float(value)
        except ValueError:
            raise DecisionError(
                f"{path}: rule_threshold.{name} `{value}` is not a number"
            ) from None
        if not 0.0 <= option_thresholds[name] <= 1.0:
            raise DecisionError(
                f"{path}: rule_threshold.{name} must be between 0 and 1"
            )

    state_fields = tuple(
        part.strip() for part in fields["state_fields"].split(",") if part.strip()
    )
    body = "\n".join(lines[end + 1 :])
    instructions = _first_heading(body, path)

    return Question(
        id=fields["id"],
        type=fields["type"],
        state_fields=state_fields,
        options=options,
        rule_threshold=threshold,
        rule_threshold_low=threshold_low,
        instructions=instructions,
        path=path,
        option_thresholds=option_thresholds,
    )


def _first_heading(body: str, path: Path) -> str:
    for line in body.split("\n"):
        heading = _HEADING.match(line)
        if heading and heading.group(1) == "#":
            return heading.group(2)
    raise DecisionError(f"{path}: the body states no question as a `# ` heading")


def default_decisions_dir() -> Path:
    """Where the questions live relative to this script, installed or in a checkout."""
    return Path(__file__).resolve().parent.parent / "orchestration" / "decisions"


def load_question(question_id: str, decisions_dir: Path) -> Question:
    path = decisions_dir / f"{question_id.replace('.', '-')}.yaml"
    if not path.is_file():
        raise DecisionError(f"no question file for `{question_id}` at {path}")
    return parse_question(path.read_text(encoding="utf-8"), path)


# --- answering a question --------------------------------------------------------------


def _unresolved(
    question: Question,
    *,
    backend: str,
    reason: str,
    probabilities: dict[str, float] | None = None,
    confidence: float | None = None,
    cost_usd: float | None = None,
) -> dict[str, object]:
    return {
        "resolved": False,
        "backend": backend,
        "reason": reason,
        "prompt": _format_prompt(question),
        "probabilities": probabilities,
        "confidence": confidence,
        "cost_usd": cost_usd,
    }


def _format_prompt(question: Question) -> str:
    if not question.options:
        return question.instructions
    options = "\n".join(f"- {name}: {text}" for name, text in question.options.items())
    return f"{question.instructions}\n{options}"


def mock_answer(question: Question) -> dict[str, object]:
    return _unresolved(question, backend="mock", reason="mock_backend")


def _validate_state(state: dict[str, object]) -> None:
    """`state` is a keyed object. A caller that hands a bare list has referenced its
    items by position, which the interface refuses rather than serialise faithfully."""
    for key, value in state.items():
        if isinstance(value, (list, tuple)):
            raise DecisionError(
                f"state field `{key}` is a list; key each item or embed it in the "
                "question's own text instead of referencing it by position"
            )


def _question_payload(question: Question) -> dict[str, object]:
    if question.type in ("choice", "noul", "score"):
        return {
            "type": question.type,
            "instructions": question.instructions,
            "criteria": dict(question.options),
        }
    raise DecisionError(
        f"decide.py does not yet build a request for type `{question.type}`"
    )


def build_request(question: Question, state: dict[str, object]) -> dict[str, object]:
    """One question, kept for callers and tests that only ever ask one at a time."""
    return build_batch_request([(question, state)])


def build_batch_request(
    items: list[tuple[Question, dict[str, object]]]
) -> dict[str, object]:
    """Several distinct questions, one shared state object, one request."""
    ids = [question.id for question, _ in items]
    if len(set(ids)) != len(ids):
        raise DecisionError("decide_many: question ids must be distinct within one call")

    combined_state: dict[str, object] = {}
    for _, state in items:
        _validate_state(state)
        for key, value in state.items():
            if key in combined_state and combined_state[key] != value:
                raise DecisionError(
                    f"decide_many: conflicting values for shared state field `{key}`"
                )
            combined_state[key] = value

    return {
        "model": MODEL_ID,
        "state": combined_state,
        "questions": {question.id: _question_payload(question) for question, _ in items},
    }


def parse_response(question: Question, response: dict[str, object]) -> dict[str, object]:
    answer = response["answers"][question.id]  # type: ignore[index]
    if answer["type"] != question.type:
        raise DecisionError(
            f"expected a {question.type} answer for `{question.id}`, got `{answer['type']}`"
        )
    cost_usd = response.get("usage", {}).get("cost")  # type: ignore[union-attr]

    if question.type == "choice":
        probabilities = answer["probabilities"]
        confidence = answer["confidence"]
        choice = answer["choice"]
        top_probability = probabilities.get(choice, 0.0)
        if top_probability >= question.rule_threshold:
            return {
                "resolved": True,
                "decision": choice,
                "probabilities": probabilities,
                "confidence": confidence,
                "backend": "jev",
                "cost_usd": cost_usd,
            }
        return _unresolved(
            question,
            backend="jev",
            reason="below_threshold",
            probabilities=probabilities,
            confidence=confidence,
            cost_usd=cost_usd,
        )

    if question.type == "noul":
        probability = answer["noul"]
        if not isinstance(probability, (int, float)):
            raise DecisionError(f"noul answer for `{question.id}` is not a number")
        probabilities = {"true": probability, "false": 1.0 - probability}
        if probability >= question.rule_threshold:
            return {
                "resolved": True,
                "decision": "true",
                "probabilities": probabilities,
                "confidence": probability,
                "backend": "jev",
                "cost_usd": cost_usd,
            }
        if probability <= question.rule_threshold_low:  # type: ignore[operator]
            return {
                "resolved": True,
                "decision": "false",
                "probabilities": probabilities,
                "confidence": 1.0 - probability,
                "backend": "jev",
                "cost_usd": cost_usd,
            }
        return _unresolved(
            question,
            backend="jev",
            reason="between_thresholds",
            probabilities=probabilities,
            confidence=max(probability, 1.0 - probability),
            cost_usd=cost_usd,
        )

    if question.type == "score":
        probabilities = answer["probabilities"]
        confidence = answer["confidence"]
        for name in question.options:
            threshold = question.option_thresholds.get(name)
            if threshold is not None and probabilities[name] >= threshold:
                return {
                    "resolved": True,
                    "decision": name,
                    "probabilities": probabilities,
                    "confidence": confidence,
                    "backend": "jev",
                    "cost_usd": cost_usd,
                }
        return _unresolved(
            question,
            backend="jev",
            reason="below_threshold",
            probabilities=probabilities,
            confidence=confidence,
            cost_usd=cost_usd,
        )

    raise DecisionError(f"decide.py does not yet parse a response for type `{question.type}`")


def _post(body: dict[str, object], api_key: str, timeout: float) -> dict[str, object]:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def call_jev_many(
    items: list[tuple[Question, dict[str, object]]],
    api_key: str | None,
    *,
    total_budget: float = TOTAL_BUDGET_SECONDS,
) -> list[dict[str, object]]:
    """One request for every distinct question, one retry on a network error or a
    retriable status, both tries together bounded by `total_budget` — never left to the
    network's own timeout. A failure at any stage degrades every question in the call to
    the same unresolved shape a lone `decide()` call would have returned for it."""
    questions = [question for question, _ in items]
    if not api_key:
        return [
            _unresolved(question, backend="jev", reason="OPENROUTER_API_KEY not set")
            for question in questions
        ]

    try:
        body = build_batch_request(items)
    except DecisionError as error:
        return [
            _unresolved(question, backend="jev", reason=str(error)) for question in questions
        ]

    deadline = time.monotonic() + total_budget
    last_reason = "unreachable"
    for attempt in range(2):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            last_reason = "time budget exhausted"
            break
        try:
            response = _post(body, api_key, timeout=remaining)
        except urllib.error.HTTPError as error:
            if attempt == 0 and error.code in RETRIABLE_STATUSES:
                last_reason = f"HTTP {error.code}, retrying"
                continue
            return [
                _unresolved(question, backend="jev", reason=f"HTTP {error.code}")
                for question in questions
            ]
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_reason = f"unreachable: {error}"
            if attempt == 0:
                continue
            return [
                _unresolved(question, backend="jev", reason=last_reason)
                for question in questions
            ]
        try:
            return [parse_response(question, response) for question in questions]
        except (KeyError, TypeError, DecisionError) as error:
            return [
                _unresolved(question, backend="jev", reason=f"malformed response: {error}")
                for question in questions
            ]

    return [
        _unresolved(question, backend="jev", reason=last_reason) for question in questions
    ]


def call_jev(
    question: Question,
    state: dict[str, object],
    api_key: str | None,
    *,
    total_budget: float = TOTAL_BUDGET_SECONDS,
) -> dict[str, object]:
    """One question, kept for callers and tests that only ever ask one at a time."""
    return call_jev_many([(question, state)], api_key, total_budget=total_budget)[0]


def decide_many(
    items: list[tuple[Question, dict[str, object]]],
    backend: str,
    *,
    api_key: str | None = None,
    total_budget: float = TOTAL_BUDGET_SECONDS,
) -> list[dict[str, object]]:
    if backend == "mock":
        return [mock_answer(question) for question, _ in items]
    if backend == "jev":
        return call_jev_many(items, api_key, total_budget=total_budget)
    raise DecisionError(f"unknown backend `{backend}`; the backends are {', '.join(sorted(BACKENDS))}")


def decide(
    question: Question,
    state: dict[str, object],
    backend: str,
    *,
    api_key: str | None = None,
) -> dict[str, object]:
    return decide_many([(question, state)], backend, api_key=api_key)[0]


# --- the journal -------------------------------------------------------------------


def state_hash(state: dict[str, object]) -> str:
    canonical = json.dumps(state, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def journal_entry(question: Question, state: dict[str, object], outcome: dict[str, object]) -> dict[str, object]:
    resolved = bool(outcome["resolved"])
    return {
        "question": question.id,
        "state_sha256": state_hash(state),
        "probabilities": outcome.get("probabilities"),
        "confidence": outcome.get("confidence"),
        "decision": outcome.get("decision") if resolved else None,
        "rule_applied": f">= {question.rule_threshold}" if resolved else str(outcome.get("reason")),
        "backend": outcome["backend"],
        "resolution": None,
    }


def journal_path(project: Path) -> Path:
    return project / ".harnex" / "state" / "journal.jsonl"


def append_journal(project: Path, entry: dict[str, object]) -> None:
    path = journal_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


# --- the command line ---------------------------------------------------------------


def _project_backend(project: Path) -> str:
    choices_path = project / setup_script.CHOICES
    if not choices_path.is_file():
        return "mock"
    choices = setup_script.parse_choices(
        choices_path.read_text(encoding="utf-8"), str(choices_path)
    )
    backend = str(choices.get("decision_model", "mock"))
    return backend if backend in BACKENDS else "mock"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Answer one typed decision question, through a real backend or by asking the person."
    )
    parser.add_argument("verb", choices=("ask",))
    parser.add_argument("--question", required=True, help="the question id, e.g. phase.route")
    parser.add_argument("--state", required=True, help="a JSON file of the state, or - for stdin")
    parser.add_argument(
        "--project", default=".", help="the project whose .harnex.yml and journal this call belongs to"
    )
    parser.add_argument(
        "--decisions-dir", type=Path, default=None, help="read questions from here instead of beside this script"
    )
    args = parser.parse_args(argv)

    project = Path(args.project).resolve()
    decisions_dir = args.decisions_dir or default_decisions_dir()

    try:
        question = load_question(args.question, decisions_dir)
        state_text = sys.stdin.read() if args.state == "-" else Path(args.state).read_text("utf-8")
        state = json.loads(state_text)
        if not isinstance(state, dict):
            raise DecisionError("the state must be a JSON object, keyed by field name")
        backend = _project_backend(project)
        outcome = decide(question, state, backend, api_key=os.environ.get("OPENROUTER_API_KEY"))
    except (DecisionError, setup_script.SetupError, OSError, json.JSONDecodeError) as error:
        print(f"decide: {error}", file=sys.stderr)
        return 1

    append_journal(project, journal_entry(question, state, outcome))
    print(json.dumps(outcome))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
