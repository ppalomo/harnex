"""The reader update uses to turn `.harnex.yml` into the `Answers` setup already validates.

No session assembles an answers document on update's behalf, so the reader has to read
the project's own recorded choices itself — this is `design.md` D2's own reader, read
against the real file at this repository's root and against a file outside the flat
shape it accepts.
"""

from pathlib import Path

import pytest

import setup
import update


def test_the_real_choices_file_reads_into_the_answers_setup_already_validates(
    repo_root: Path, plugin_root: Path
) -> None:
    text = (repo_root / ".harnex.yml").read_text(encoding="utf-8")
    answers = update.read_choices(text, plugin_root)

    assert answers.project_name == "harnex"
    assert answers.profiles == ()
    assert answers.sets == ("canary", "code", "git", "language", "sdd")
    assert answers.features == ()
    assert answers.canary == "Hullaballoo!"
    assert answers.decision_model == "jev"
    assert answers.check_command == "uv run --with pytest pytest"

    # Nothing is approved on update's behalf: there is no session to have approved it.
    assert answers.pointer_agents is False
    assert answers.pointer_claude is False
    assert answers.mcp_playwright is False
    assert answers.adopt == ()


@pytest.mark.parametrize(
    "answers",
    [
        setup.Answers(
            project_name="scratch",
            profiles=("fastapi", "react"),
            sets=("canary", "code", "git", "language", "sdd"),
            features=(),
            canary="Hullaballoo!",
            decision_model="mock",
            check_command="make check",
        ),
        setup.Answers(
            project_name="scratch",
            profiles=(),
            sets=("code",),
            features=(),
            canary="",
            decision_model="jev",
            check_command="uv run --with pytest pytest",
        ),
    ],
    ids=["non-empty lists", "empty lists"],
)
def test_the_rendered_template_round_trips_through_the_reader(
    plugin_root: Path, answers: "setup.Answers"
) -> None:
    """`design.md`'s own Risks mitigation: the template and the reader must agree about
    `.harnex.yml`'s shape. This fails the moment one of them changes without the other."""
    rendered = setup.render_template(
        plugin_root, "harnex.yml", {"keys": setup.format_choices(answers).rstrip("\n")}
    )

    round_tripped = update.read_choices(rendered, plugin_root)

    assert round_tripped.project_name == answers.project_name
    assert round_tripped.profiles == answers.profiles
    assert round_tripped.sets == answers.sets
    assert round_tripped.features == answers.features
    assert round_tripped.canary == answers.canary
    assert round_tripped.decision_model == answers.decision_model
    assert round_tripped.check_command == answers.check_command


def test_a_shape_outside_the_flat_one_is_a_read_error_not_a_crash(plugin_root: Path) -> None:
    malformed = (
        "project_name: scratch\n"
        "profiles:\n"
        "sets:\n"
        "  nested: mapping\n"
        "features:\n"
        "canary: Hullaballoo!\n"
        "decision_model: mock\n"
        "check_command: make check\n"
    )
    with pytest.raises(setup.SetupError) as refusal:
        update.read_choices(malformed, plugin_root)
    assert "not `key: value`" in str(refusal.value)
