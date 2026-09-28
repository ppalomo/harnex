"""`decide.py`: the question-file format, both backends, the journal, and the CLI.

The `jev` fixtures below are the exact request and response shapes OpenRouter's own docs
show for its Decisions endpoint (`POST /api/alpha/decisions`, model `typesafe/jev-1.13`),
read while designing this change — not invented. A mismatch here after a live call is a
reason to fix this file, not the other way around.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import time
import urllib.error
from pathlib import Path

import pytest

import decide

GOOD_QUESTION = """\
id: a.question
type: choice
state_fields: phase, task
option.account: Login, permissions, or profile issues.
option.frontend: Rendering, layout, or browser compatibility issues.
option.payments: Checkout, billing, or payment processing issues.
rule_threshold: 0.7
---

# Which team should own this ticket?

Some prose a person or a model reads; `decide.py` never parses it.
"""


def _seed(tmp_path: Path, text: str, name: str = "a-question.yaml") -> Path:
    (tmp_path / name).write_text(text, encoding="utf-8")
    return tmp_path


def _question(tmp_path: Path, text: str = GOOD_QUESTION) -> decide.Question:
    directory = _seed(tmp_path, text)
    return decide.load_question("a.question", directory)


# --- the question-file format --------------------------------------------------------


def test_a_good_question_parses(tmp_path: Path) -> None:
    question = _question(tmp_path)
    assert question.id == "a.question"
    assert question.type == "choice"
    assert question.state_fields == ("phase", "task")
    assert question.options == {
        "account": "Login, permissions, or profile issues.",
        "frontend": "Rendering, layout, or browser compatibility issues.",
        "payments": "Checkout, billing, or payment processing issues.",
    }
    assert question.rule_threshold == 0.7
    assert question.instructions == "Which team should own this ticket?"


@pytest.mark.parametrize(
    ("fault", "text", "expected"),
    [
        ("no delimiter", GOOD_QUESTION.replace("---\n", ""), "no bare"),
        ("a missing field", GOOD_QUESTION.replace("state_fields: phase, task\n", ""), "declares no state_fields"),
        ("an unknown field", GOOD_QUESTION.replace("id: a.question", "id: a.question\nseverity: high"), "does not hold"),
        ("a duplicate option", GOOD_QUESTION.replace("rule_threshold:", "option.account: again\nrule_threshold:"), "declared twice"),
        ("a bad type", GOOD_QUESTION.replace("type: choice", "type: vibes"), "is not one of"),
        ("a threshold out of range", GOOD_QUESTION.replace("rule_threshold: 0.7", "rule_threshold: 1.7"), "between 0 and 1"),
        ("a non-numeric threshold", GOOD_QUESTION.replace("rule_threshold: 0.7", "rule_threshold: high"), "is not a number"),
        ("no heading in the body", GOOD_QUESTION.replace("# Which team should own this ticket?\n", ""), "states no question"),
    ],
    ids=lambda p: p if isinstance(p, str) else "",
)
def test_the_format_check_catches(tmp_path: Path, fault: str, text: str, expected: str) -> None:
    directory = _seed(tmp_path, text)
    with pytest.raises(decide.DecisionError, match=expected):
        decide.load_question("a.question", directory)


def test_a_choice_question_with_no_options_is_refused(tmp_path: Path) -> None:
    lines = [line for line in GOOD_QUESTION.splitlines(keepends=True) if not line.startswith("option.")]
    with pytest.raises(decide.DecisionError, match="declares no `option"):
        decide.parse_question("".join(lines), tmp_path / "a-question.yaml")


def test_the_real_phase_route_question_parses(plugin_root: Path) -> None:
    question = decide.load_question("phase.route", plugin_root / "orchestration" / "decisions")
    assert question.type == "choice"
    assert set(question.options) == {"codex", "claude-sonnet", "claude-opus", "claude-fable", "human"}
    assert question.rule_threshold == 0.70


# --- the mock backend -----------------------------------------------------------------


def test_mock_never_opens_a_socket(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    question = _question(tmp_path)

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the mock backend must never make a network call")

    monkeypatch.setattr(decide.urllib.request, "urlopen", _boom)
    outcome = decide.decide(question, {"phase": "explore", "task": "an idea"}, "mock")
    assert outcome == {
        "resolved": False,
        "backend": "mock",
        "reason": "mock_backend",
        "prompt": outcome["prompt"],
        "probabilities": None,
        "confidence": None,
        "cost_usd": None,
    }
    assert "Which team should own this ticket?" in outcome["prompt"]
    assert "account:" in outcome["prompt"]


# --- building the jev request, from the verified OpenRouter shape ----------------------


def test_build_request_matches_the_documented_shape(tmp_path: Path) -> None:
    question = _question(tmp_path)
    state = {"phase": "propose", "task": "checkout is blank after Pay"}
    request = decide.build_request(question, state)
    assert request == {
        "model": "typesafe/jev-1.13",
        "state": state,
        "questions": {
            "a.question": {
                "type": "choice",
                "instructions": "Which team should own this ticket?",
                "criteria": {
                    "account": "Login, permissions, or profile issues.",
                    "frontend": "Rendering, layout, or browser compatibility issues.",
                    "payments": "Checkout, billing, or payment processing issues.",
                },
            }
        },
    }


def test_build_request_refuses_a_positional_list_in_state(tmp_path: Path) -> None:
    question = _question(tmp_path)
    with pytest.raises(decide.DecisionError, match="referencing it by position"):
        decide.build_request(question, {"phase": "propose", "candidates": ["a", "b", "c"]})


# --- reading the jev response, from the verified OpenRouter shape ----------------------

DOCUMENTED_RESPONSE = {
    "id": "gen-dec-1789738314-X5e5eKGQdvR9rblyX250",
    "model": "typesafe/jev-1.13-20260917",
    "provider": "TypeSafe",
    "answers": {
        "a.question": {
            "type": "choice",
            "choice": "payments",
            "confidence": 0.75,
            "probabilities": {"account": 0, "frontend": 0.16, "payments": 0.84},
        }
    },
    "usage": {"input_tokens": 476, "output_tokens": 70, "cost": 0.000019992},
}


def test_a_confident_answer_resolves(tmp_path: Path) -> None:
    question = _question(tmp_path)  # rule_threshold 0.7, documented probability 0.84
    outcome = decide.parse_response(question, DOCUMENTED_RESPONSE)
    assert outcome == {
        "resolved": True,
        "decision": "payments",
        "probabilities": {"account": 0, "frontend": 0.16, "payments": 0.84},
        "confidence": 0.75,
        "backend": "jev",
        "cost_usd": 0.000019992,
    }


def test_a_low_confidence_answer_does_not_resolve(tmp_path: Path) -> None:
    text = GOOD_QUESTION.replace("rule_threshold: 0.7", "rule_threshold: 0.9")
    question = _question(tmp_path, text)
    outcome = decide.parse_response(question, DOCUMENTED_RESPONSE)
    assert outcome["resolved"] is False
    assert outcome["reason"] == "below_threshold"
    assert outcome["backend"] == "jev"
    assert outcome["probabilities"] == {"account": 0, "frontend": 0.16, "payments": 0.84}


# --- the jev backend's failure handling -------------------------------------------------


def test_no_api_key_never_calls_the_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    question = _question(tmp_path)
    calls = []
    monkeypatch.setattr(decide, "_post", lambda *a, **k: calls.append(1))
    outcome = decide.call_jev(question, {"phase": "propose", "task": "x"}, api_key=None)
    assert outcome == {
        "resolved": False,
        "backend": "jev",
        "reason": "OPENROUTER_API_KEY not set",
        "prompt": outcome["prompt"],
        "probabilities": None,
        "confidence": None,
        "cost_usd": None,
    }
    assert not calls


def test_a_5xx_is_retried_once_and_then_succeeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    question = _question(tmp_path)
    calls = []

    def _post(_body: dict, _key: str, timeout: float) -> dict:
        calls.append(timeout)
        if len(calls) == 1:
            raise urllib.error.HTTPError("url", 503, "unavailable", {}, None)
        return DOCUMENTED_RESPONSE

    monkeypatch.setattr(decide, "_post", _post)
    outcome = decide.call_jev(question, {"phase": "propose", "task": "x"}, api_key="k")
    assert len(calls) == 2
    assert outcome["resolved"] is True
    assert outcome["decision"] == "payments"


def test_a_4xx_is_not_retried(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    question = _question(tmp_path)
    calls = []

    def _post(_body: dict, _key: str, timeout: float) -> dict:
        calls.append(1)
        raise urllib.error.HTTPError("url", 401, "unauthorized", {}, None)

    monkeypatch.setattr(decide, "_post", _post)
    outcome = decide.call_jev(question, {"phase": "propose", "task": "x"}, api_key="k")
    assert len(calls) == 1
    assert outcome["resolved"] is False
    assert outcome["reason"] == "HTTP 401"


def test_two_network_failures_both_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    question = _question(tmp_path)
    calls = []

    def _post(_body: dict, _key: str, timeout: float) -> dict:
        calls.append(1)
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr(decide, "_post", _post)
    outcome = decide.call_jev(question, {"phase": "propose", "task": "x"}, api_key="k")
    assert len(calls) == 2
    assert outcome["resolved"] is False
    assert "unreachable" in outcome["reason"]


def test_a_malformed_response_does_not_raise(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    question = _question(tmp_path)
    monkeypatch.setattr(decide, "_post", lambda *a, **k: {"no": "answers key here"})
    outcome = decide.call_jev(question, {"phase": "propose", "task": "x"}, api_key="k")
    assert outcome["resolved"] is False
    assert "malformed response" in outcome["reason"]


def test_the_retry_stops_once_the_time_budget_is_gone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A hanging first attempt must not buy a second one past the stated budget."""
    question = _question(tmp_path)
    calls = []
    clock = [0.0]

    def _monotonic() -> float:
        return clock[0]

    def _post(_body: dict, _key: str, timeout: float) -> dict:
        calls.append(1)
        clock[0] += 10.0  # the attempt "took" longer than the whole budget
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(decide.time, "monotonic", _monotonic)
    monkeypatch.setattr(decide, "_post", _post)
    outcome = decide.call_jev(
        question, {"phase": "propose", "task": "x"}, api_key="k", total_budget=3.0
    )
    assert len(calls) == 1, "a second attempt was made after the budget was already spent"
    assert outcome["resolved"] is False


# --- the journal -----------------------------------------------------------------------


def test_every_call_appends_exactly_one_line(tmp_path: Path) -> None:
    question = _question(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    outcome = decide.mock_answer(question)
    decide.append_journal(project, decide.journal_entry(question, {"phase": "propose"}, outcome))
    lines = decide.journal_path(project).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["question"] == "a.question"
    assert entry["backend"] == "mock"
    assert entry["decision"] is None
    assert entry["resolution"] is None
    assert len(entry["state_sha256"]) == 64


def test_a_resolved_call_journals_its_decision(tmp_path: Path) -> None:
    question = _question(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    outcome = decide.parse_response(question, DOCUMENTED_RESPONSE)
    decide.append_journal(project, decide.journal_entry(question, {"phase": "propose"}, outcome))
    entry = json.loads(decide.journal_path(project).read_text(encoding="utf-8").splitlines()[0])
    assert entry["decision"] == "payments"
    assert entry["backend"] == "jev"


# --- the CLI, run as a real process ------------------------------------------------------

_FULL_HARNEX_YML = """\
project_name: scratch
profiles:
sets:
  - git
features:
canary: ""
decision_model: mock
check_command: make check
"""

requires_uv = pytest.mark.skipif(shutil.which("uv") is None, reason="uv is how the host runs this script")


@requires_uv
def test_ask_as_a_real_process_with_mock(tmp_path: Path, repo_root: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".harnex.yml").write_text(_FULL_HARNEX_YML, encoding="utf-8")
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"phase": "explore", "task": "an idea", "profiles": []}))

    script = repo_root / "plugin" / "scripts" / "decide.py"
    start = time.monotonic()
    finished = subprocess.run(
        ["uv", "run", "--quiet", str(script), "ask", "--question", "phase.route", "--state", str(state_file), "--project", str(project)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    elapsed = time.monotonic() - start
    assert finished.returncode == 0, finished.stderr
    assert elapsed < decide.TOTAL_BUDGET_SECONDS + 10  # generous ceiling; uv start-up dominates

    outcome = json.loads(finished.stdout)
    assert outcome["resolved"] is False
    assert outcome["backend"] == "mock"

    journal = json.loads((project / ".harnex" / "state" / "journal.jsonl").read_text().splitlines()[0])
    assert journal["question"] == "phase.route"
    assert journal["backend"] == "mock"


@requires_uv
def test_ask_defaults_to_mock_with_no_harnex_yml(tmp_path: Path, repo_root: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"phase": "explore", "task": "an idea", "profiles": []}))

    script = repo_root / "plugin" / "scripts" / "decide.py"
    finished = subprocess.run(
        ["uv", "run", "--quiet", str(script), "ask", "--question", "phase.route", "--state", str(state_file), "--project", str(project)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert finished.returncode == 0, finished.stderr
    assert json.loads(finished.stdout)["backend"] == "mock"
