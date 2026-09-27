"""The canary check, over the recorded `stop.json` and faults derived from it in code.

The cases below are never written by hand: each one starts from the real fixture and
changes exactly one thing, so the shape every case is tested against is the host's, per
`docs/decisions/` and the design's D9.
"""

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

import canary  # a plugin script, reached by path (see conftest)

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = json.loads(
    (REPO_ROOT / "tests" / "fixtures" / "hooks" / "2.1.267" / "stop.json").read_text(
        encoding="utf-8"
    )
)
WORD = "Hullaballoo!"

CHOICES = """\
project_name: scratch
profiles:
sets:
  - canary
features:
canary: {word}
decision_model: mock
check_command: make check
"""

CHOICES_SET_NOT_CHOSEN = """\
project_name: scratch
profiles:
sets:
  - git
features:
canary: ""
decision_model: mock
check_command: make check
"""

CHOICES_NO_WORD = """\
project_name: scratch
profiles:
sets:
  - canary
features:
canary: ""
decision_model: mock
check_command: make check
"""


def _project(tmp_path: Path, choices_text: str | None) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    if choices_text is not None:
        (project / ".harnex.yml").write_text(choices_text, encoding="utf-8")
    return project


def _payload(**overrides: object) -> dict:
    payload = dict(FIXTURE)
    payload.update(overrides)
    return payload


def _run(
    monkeypatch: pytest.MonkeyPatch, project: Path, stdin_text: str
) -> tuple[int, dict | None]:
    """Run the check the way the host does: stdin in, exit code and stdout out."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_text))
    out = io.StringIO()
    with redirect_stdout(out):
        code = canary.main()
    text = out.getvalue().strip()
    return code, (json.loads(text) if text else None)


@pytest.mark.parametrize(
    ("answer", "expect_warning"),
    [
        (f"All good. {WORD}", False),
        (f"All good. **{WORD}**", False),
        (f"All good. *{WORD}*", False),
        (f"All good. `{WORD}`", False),
        ("All good. Nothing here.", True),
        (f"{WORD} appears here, then more text follows.", True),
        (f"All good. {WORD.lower()}", True),
    ],
    ids=[
        "word-present",
        "word-in-bold",
        "word-in-italics",
        "word-in-code",
        "word-missing",
        "word-mid-answer",
        "word-in-another-case",
    ],
)
def test_the_word_check(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, answer: str, expect_warning: bool
) -> None:
    project = _project(tmp_path, CHOICES.format(word=WORD))
    code, message = _run(
        monkeypatch, project, json.dumps(_payload(last_assistant_message=answer))
    )
    assert code == 0
    if expect_warning:
        assert message is not None
        assert "decision" not in message
        assert WORD in message["systemMessage"]
    else:
        assert message is None


def test_a_project_word_other_than_the_one_proposed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The word comes only from the project; the check holds no default of its own."""
    project_word = "Zorglub"
    project = _project(tmp_path, CHOICES.format(word=project_word))
    code, message = _run(
        monkeypatch,
        project,
        json.dumps(_payload(last_assistant_message=f"Done. {WORD}")),
    )
    assert code == 0
    assert message is not None
    assert project_word in message["systemMessage"]


def test_no_harnex_yml(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project = _project(tmp_path, None)
    code, message = _run(monkeypatch, project, json.dumps(_payload()))
    assert code == 0
    assert message is None


def test_set_not_chosen(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project = _project(tmp_path, CHOICES_SET_NOT_CHOSEN)
    code, message = _run(monkeypatch, project, json.dumps(_payload()))
    assert code == 0
    assert message is None


def test_set_chosen_without_a_word(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project = _project(tmp_path, CHOICES_NO_WORD)
    code, message = _run(monkeypatch, project, json.dumps(_payload()))
    assert code == 0
    assert message is not None
    assert "not checked" in message["systemMessage"]
    assert "no word is recorded" in message["systemMessage"]


def test_unreadable_harnex_yml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project = _project(tmp_path, "not: valid: : yaml: [broken\n")
    code, message = _run(monkeypatch, project, json.dumps(_payload()))
    assert code == 0
    assert message is not None
    assert "not checked" in message["systemMessage"]


def test_field_absent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project = _project(tmp_path, CHOICES.format(word=WORD))
    payload = dict(FIXTURE)
    del payload["last_assistant_message"]
    code, message = _run(monkeypatch, project, json.dumps(payload))
    assert code == 0
    assert message is None


def test_field_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project = _project(tmp_path, CHOICES.format(word=WORD))
    code, message = _run(
        monkeypatch, project, json.dumps(_payload(last_assistant_message=""))
    )
    assert code == 0
    assert message is None


def test_malformed_stdin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project = _project(tmp_path, CHOICES.format(word=WORD))
    code, message = _run(monkeypatch, project, "not json")
    assert code == 0
    assert message is not None
    assert "not checked" in message["systemMessage"]
