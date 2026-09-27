"""The canary check is tested against what the host really sends, not its docs.

`tests/fixtures/hooks/<version>/` holds end-of-turn payloads recorded from a real
Claude Code session, sanitised of paths and identifiers. This is the one test that
would catch the host renaming or dropping the field the canary check reads:
`last_assistant_message`. It is deliberately independent of `canary.py` itself, so a
bug in the check cannot hide a fixture that has gone stale.
"""

import json
from pathlib import Path

import pytest

HOST_VERSION = "2.1.267"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "hooks" / HOST_VERSION
STOP_FIXTURE = FIXTURES_DIR / "stop.json"

ANSWER_FIELD = "last_assistant_message"


def _assert_carries_the_answer(payload: dict, path: Path, host_version: str) -> None:
    if not payload.get(ANSWER_FIELD):
        raise AssertionError(
            f"{path}: does not carry the answer text in `{ANSWER_FIELD}`, the field the "
            f"canary check reads. Recorded against Claude Code {host_version}; the host "
            "may have renamed or dropped it."
        )


def test_the_stop_fixture_carries_the_answer_text() -> None:
    payload = json.loads(STOP_FIXTURE.read_text(encoding="utf-8"))
    _assert_carries_the_answer(payload, STOP_FIXTURE, HOST_VERSION)


def test_the_check_catches_the_field_renamed(tmp_path: Path) -> None:
    """The check fails on a fixture it should reject, not only passes on the real one."""
    payload = json.loads(STOP_FIXTURE.read_text(encoding="utf-8"))
    payload["last_assistant_answer"] = payload.pop(ANSWER_FIELD)
    broken = tmp_path / "stop.json"
    broken.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(AssertionError) as excinfo:
        _assert_carries_the_answer(
            json.loads(broken.read_text(encoding="utf-8")), broken, HOST_VERSION
        )
    assert ANSWER_FIELD in str(excinfo.value)
    assert HOST_VERSION in str(excinfo.value)
