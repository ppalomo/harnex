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


def test_a_choice_question_cannot_declare_rule_threshold_low(tmp_path: Path) -> None:
    text = GOOD_QUESTION.replace("rule_threshold: 0.7", "rule_threshold: 0.7\nrule_threshold_low: 0.3")
    with pytest.raises(decide.DecisionError, match="only a noul question may declare"):
        decide.parse_question(text, tmp_path / "a-question.yaml")


# --- the score type ---------------------------------------------------------------------

SCORE_QUESTION = """\
id: a.score
type: score
state_fields: command
option.destructive: The command may cause destructive changes.
option.read_only: The command only reads state.
option.reversible: The command makes reversible changes.
rule_threshold.destructive: 0.30
rule_threshold.read_only: 0.85
---

# What risk does this command carry?
"""


def _score_question(tmp_path: Path, text: str = SCORE_QUESTION) -> decide.Question:
    directory = _seed(tmp_path, text, name="a-score.yaml")
    return decide.load_question("a.score", directory)


def test_a_good_score_question_parses_with_per_option_thresholds(tmp_path: Path) -> None:
    question = _score_question(tmp_path)
    assert question.type == "score"
    assert question.option_thresholds == {"destructive": 0.30, "read_only": 0.85}


def test_score_build_request_includes_every_option_as_criteria(tmp_path: Path) -> None:
    question = _score_question(tmp_path)
    state = {"command": "git status"}
    request = decide.build_request(question, state)
    assert request == {
        "model": "typesafe/jev-1.13",
        "state": state,
        "questions": {
            "a.score": {
                "type": "score",
                "instructions": "What risk does this command carry?",
                "criteria": {
                    "destructive": "The command may cause destructive changes.",
                    "read_only": "The command only reads state.",
                    "reversible": "The command makes reversible changes.",
                },
            }
        },
    }


def test_a_score_question_needs_a_per_option_threshold(tmp_path: Path) -> None:
    text = "\n".join(
        line for line in SCORE_QUESTION.splitlines() if not line.startswith("rule_threshold.")
    )
    with pytest.raises(
        decide.DecisionError, match=r"a-score\.yaml.*rule_threshold\."
    ):
        decide.parse_question(text, tmp_path / "a-score.yaml")


@pytest.mark.parametrize(
    ("flat_field", "expected"),
    [
        ("rule_threshold: 0.70", "rule_threshold"),
        ("rule_threshold_low: 0.30", "rule_threshold_low"),
    ],
)
def test_a_score_question_forbids_flat_threshold_fields(
    tmp_path: Path, flat_field: str, expected: str
) -> None:
    text = SCORE_QUESTION.replace("---", f"{flat_field}\n---")
    with pytest.raises(
        decide.DecisionError, match=rf"a-score\.yaml.*{expected}"
    ):
        decide.parse_question(text, tmp_path / "a-score.yaml")


SCORE_RESPONSE = {
    "answers": {
        "a.score": {
            "type": "score",
            "score": 0.0,
            "probabilities": {
                "destructive": 0.20,
                "read_only": 0.86,
                "reversible": 0.90,
            },
            "confidence": 0.86,
        }
    },
    "usage": {"cost": 0.00001},
}


def test_score_one_option_crossing_its_threshold_resolves(tmp_path: Path) -> None:
    question = _score_question(tmp_path)
    outcome = decide.parse_response(question, SCORE_RESPONSE)
    assert outcome == {
        "resolved": True,
        "decision": "read_only",
        "probabilities": {
            "destructive": 0.20,
            "read_only": 0.86,
            "reversible": 0.90,
        },
        "confidence": 0.86,
        "backend": "jev",
        "cost_usd": 0.00001,
    }


def test_score_two_options_crossing_resolves_the_earliest_declared(tmp_path: Path) -> None:
    question = _score_question(tmp_path)
    response = {
        "answers": {
            "a.score": {
                "type": "score",
                "score": 0.0,
                "probabilities": {
                    "destructive": 0.31,
                    "read_only": 0.99,
                    "reversible": 0.90,
                },
                "confidence": 0.99,
            }
        },
        "usage": {"cost": 0.00001},
    }
    outcome = decide.parse_response(question, response)
    assert outcome["resolved"] is True
    assert outcome["decision"] == "destructive"
    assert outcome["probabilities"] == response["answers"]["a.score"]["probabilities"]


def test_score_with_no_option_crossing_is_unresolved(tmp_path: Path) -> None:
    question = _score_question(tmp_path)
    response = {
        "answers": {
            "a.score": {
                "type": "score",
                "score": 0.0,
                "probabilities": {
                    "destructive": 0.29,
                    "read_only": 0.84,
                    "reversible": 0.99,
                },
                "confidence": 0.99,
            }
        },
        "usage": {"cost": 0.00001},
    }
    outcome = decide.parse_response(question, response)
    assert outcome["resolved"] is False
    assert outcome["reason"] == "below_threshold"
    assert outcome["probabilities"] == response["answers"]["a.score"]["probabilities"]
    assert "What risk does this command carry?" in outcome["prompt"]


def test_score_mock_backend_returns_the_generic_unresolved_outcome(tmp_path: Path) -> None:
    question = _score_question(tmp_path)
    outcome = decide.decide(question, {"command": "git status"}, "mock")
    assert outcome == {
        "resolved": False,
        "backend": "mock",
        "reason": "mock_backend",
        "prompt": outcome["prompt"],
        "probabilities": None,
        "confidence": None,
        "cost_usd": None,
    }
    assert "What risk does this command carry?" in outcome["prompt"]


# --- the noul type ----------------------------------------------------------------------

NOUL_QUESTION = """\
id: a.scope
type: noul
state_fields: task_text, changed_paths
option.true: The write is in scope for this task.
option.false: The write is out of scope.
rule_threshold: 0.85
rule_threshold_low: 0.35
---

# Is this write in scope for the task?

Some prose a person or a model reads; `decide.py` never parses it.
"""


def _noul_question(tmp_path: Path, text: str = NOUL_QUESTION) -> decide.Question:
    directory = _seed(tmp_path, text, name="a-scope.yaml")
    return decide.load_question("a.scope", directory)


def test_a_good_noul_question_parses(tmp_path: Path) -> None:
    question = _noul_question(tmp_path)
    assert question.type == "noul"
    assert question.options == {
        "true": "The write is in scope for this task.",
        "false": "The write is out of scope.",
    }
    assert question.rule_threshold == 0.85
    assert question.rule_threshold_low == 0.35


def test_a_noul_question_needs_rule_threshold_low(tmp_path: Path) -> None:
    text = NOUL_QUESTION.replace("rule_threshold_low: 0.35\n", "")
    with pytest.raises(decide.DecisionError, match="declares no rule_threshold_low"):
        decide.parse_question(text, tmp_path / "a-scope.yaml")


def test_a_noul_question_rejects_a_low_threshold_at_or_above_the_high_one(tmp_path: Path) -> None:
    text = NOUL_QUESTION.replace("rule_threshold_low: 0.35", "rule_threshold_low: 0.85")
    with pytest.raises(decide.DecisionError, match="must be below rule_threshold"):
        decide.parse_question(text, tmp_path / "a-scope.yaml")


def test_a_noul_question_must_declare_exactly_true_and_false(tmp_path: Path) -> None:
    text = NOUL_QUESTION.replace("option.false: The write is out of scope.\n", "")
    with pytest.raises(decide.DecisionError, match="option.true.*option.false"):
        decide.parse_question(text, tmp_path / "a-scope.yaml")


def test_noul_build_request_matches_the_documented_shape(tmp_path: Path) -> None:
    question = _noul_question(tmp_path)
    state = {"task_text": "add a favicon", "changed_paths": "plugin/assets/favicon.svg"}
    request = decide.build_request(question, state)
    assert request == {
        "model": "typesafe/jev-1.13",
        "state": state,
        "questions": {
            "a.scope": {
                "type": "noul",
                "instructions": "Is this write in scope for the task?",
                "criteria": {
                    "true": "The write is in scope for this task.",
                    "false": "The write is out of scope.",
                },
            }
        },
    }


NOUL_RESPONSE_HIGH = {
    "answers": {"a.scope": {"type": "noul", "noul": 0.96}},
    "usage": {"cost": 0.00001},
}
NOUL_RESPONSE_LOW = {
    "answers": {"a.scope": {"type": "noul", "noul": 0.04}},
    "usage": {"cost": 0.00001},
}
NOUL_RESPONSE_BETWEEN = {
    "answers": {"a.scope": {"type": "noul", "noul": 0.6}},
    "usage": {"cost": 0.00001},
}


def test_noul_above_the_high_threshold_resolves_true(tmp_path: Path) -> None:
    question = _noul_question(tmp_path)
    outcome = decide.parse_response(question, NOUL_RESPONSE_HIGH)
    assert outcome["resolved"] is True
    assert outcome["decision"] == "true"
    assert outcome["confidence"] == 0.96


def test_noul_at_or_below_the_low_threshold_resolves_false(tmp_path: Path) -> None:
    question = _noul_question(tmp_path)
    outcome = decide.parse_response(question, NOUL_RESPONSE_LOW)
    assert outcome["resolved"] is True
    assert outcome["decision"] == "false"
    assert outcome["confidence"] == pytest.approx(0.96)


def test_noul_between_the_thresholds_does_not_resolve(tmp_path: Path) -> None:
    question = _noul_question(tmp_path)
    outcome = decide.parse_response(question, NOUL_RESPONSE_BETWEEN)
    assert outcome["resolved"] is False
    assert outcome["reason"] == "between_thresholds"
    assert outcome["probabilities"] == {"true": 0.6, "false": pytest.approx(0.4)}


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


# --- decide_many: several distinct questions, one shared state, one call ---------------


def test_decide_many_with_mock_answers_each_question_on_its_own(tmp_path: Path) -> None:
    route = _question(tmp_path)
    scope = _noul_question(tmp_path)
    outcomes = decide.decide_many(
        [
            (route, {"phase": "apply", "task": "x"}),
            (scope, {"task_text": "x", "changed_paths": ""}),
        ],
        "mock",
    )
    assert len(outcomes) == 2
    assert all(outcome["resolved"] is False and outcome["reason"] == "mock_backend" for outcome in outcomes)
    assert "Which team should own this ticket?" in outcomes[0]["prompt"]
    assert "Is this write in scope for the task?" in outcomes[1]["prompt"]


def test_build_batch_request_merges_shared_state_and_keys_both_questions(tmp_path: Path) -> None:
    route = _question(tmp_path)
    scope = _noul_question(tmp_path)
    request = decide.build_batch_request(
        [
            (route, {"phase": "apply", "task": "x"}),
            (scope, {"task_text": "y", "changed_paths": "p"}),
        ]
    )
    assert request["state"] == {"phase": "apply", "task": "x", "task_text": "y", "changed_paths": "p"}
    assert set(request["questions"]) == {"a.question", "a.scope"}


def test_build_batch_request_refuses_conflicting_shared_state(tmp_path: Path) -> None:
    route = _question(tmp_path)
    scope = _noul_question(tmp_path)
    with pytest.raises(decide.DecisionError, match="conflicting values"):
        decide.build_batch_request(
            [
                (route, {"task_text": "a"}),
                (scope, {"task_text": "b", "changed_paths": "p"}),
            ]
        )


def test_build_batch_request_refuses_duplicate_question_ids(tmp_path: Path) -> None:
    route = _question(tmp_path)
    with pytest.raises(decide.DecisionError, match="must be distinct"):
        decide.build_batch_request([(route, {"task": "a"}), (route, {"task": "b"})])


def test_decide_many_with_jev_answers_both_questions_from_one_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    route = _question(tmp_path)
    scope = _noul_question(tmp_path)
    combined_response = {
        "answers": {
            "a.question": DOCUMENTED_RESPONSE["answers"]["a.question"],
            "a.scope": NOUL_RESPONSE_HIGH["answers"]["a.scope"],
        },
        "usage": {"cost": 0.00002},
    }
    calls = []

    def _post(_body: dict, _key: str, timeout: float) -> dict:
        calls.append(_body)
        return combined_response

    monkeypatch.setattr(decide, "_post", _post)
    outcomes = decide.decide_many(
        [
            (route, {"phase": "apply", "task": "x"}),
            (scope, {"task_text": "x", "changed_paths": ""}),
        ],
        "jev",
        api_key="k",
    )
    assert len(calls) == 1, "one request answered both questions"
    assert outcomes[0]["decision"] == "payments"
    assert outcomes[1]["decision"] == "true"


def test_decide_many_degrades_every_question_together_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    route = _question(tmp_path)
    scope = _noul_question(tmp_path)

    def _post(_body: dict, _key: str, timeout: float) -> dict:
        raise urllib.error.HTTPError("url", 401, "unauthorized", {}, None)

    monkeypatch.setattr(decide, "_post", _post)
    outcomes = decide.decide_many(
        [
            (route, {"phase": "apply", "task": "x"}),
            (scope, {"task_text": "x", "changed_paths": ""}),
        ],
        "jev",
        api_key="k",
    )
    assert all(outcome["resolved"] is False and outcome["reason"] == "HTTP 401" for outcome in outcomes)


def test_decide_is_a_one_question_call_through_decide_many(tmp_path: Path) -> None:
    question = _question(tmp_path)
    outcome = decide.decide(question, {"phase": "explore", "task": "an idea"}, "mock")
    assert outcome["resolved"] is False
    assert outcome["reason"] == "mock_backend"


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
