"""What a project is asked, and what the harness refuses to be told.

Two shapes meet here: the answers document the session hands the script, which is JSON
because a session writes it, and the project's own record of those answers, which is a
flat file because every later hook and command reads it. The reader of that flat file is
the schema: what it does not understand, it refuses, with the line.
"""

from pathlib import Path

import pytest

import setup


def test_the_choices_come_from_what_the_harness_holds(plugin_root: Path) -> None:
    on_offer = setup.choices_on_offer(plugin_root)
    assert on_offer["sets"] == setup.available_sets(plugin_root)
    assert on_offer["decision_models"] == list(setup.DECISION_BACKENDS)
    assert on_offer["default_canary"]


def test_a_kind_of_choice_with_nothing_to_choose_from(tmp_path: Path, plugin_root: Path) -> None:
    """Profiles and features arrive in later phases. Until then the harness holds none,
    and the question is not asked rather than asked with an empty list."""
    assert setup.available_profiles(plugin_root) == []
    assert setup.available_features(plugin_root) == []

    holding = tmp_path / "plugin"
    (holding / "tools" / "profiles" / "one").mkdir(parents=True)
    (holding / "tools" / "profiles" / "two").mkdir(parents=True)
    (holding / "tools" / "features.json").write_text('[{"name": "guard"}]', encoding="utf-8")
    assert setup.available_profiles(holding) == ["one", "two"]
    assert setup.available_features(holding) == ["guard"]


def test_the_sets_offered_follow_the_tree(tmp_path: Path) -> None:
    rules = tmp_path / "plugin" / "context" / "rules"
    for name in ("alpha", "beta"):
        directory = rules / name
        directory.mkdir(parents=True)
        (directory / f"{name}-rule.md").write_text(
            f"---\nid: {name}-rule\nset: {name}\napplies_to: always\nenforced_by: none\n---\n\n"
            f"# The {name} rule\n\nBecause a set needs a rule.\n",
            encoding="utf-8",
        )
    assert setup.available_sets(tmp_path / "plugin") == ["alpha", "beta"]


def test_the_answers_round_trip_through_the_project_s_own_file(plugin_root: Path, answers) -> None:
    read = setup.read_answers(__import__("json").dumps(answers), plugin_root)
    written = setup.format_choices(read)
    assert setup.parse_choices(written) == read.as_choices()
    assert setup.format_choices(read) == written, "the same answers are written the same way"


@pytest.mark.parametrize(
    "faulty, says",
    [
        ("project_name: a\nprofiles:\n  sub: 1\n", "not `key: value`"),
        ("project_name: a\nsets:\n\t- git\n", "not `key: value`"),
        ("project_name: a\nproject_name: b\n", "stated twice"),
        ("project_name: a\nnonsense: b\n", "unknown key"),
        ("  - git\n", "a list item before any key"),
        ("project_name: a\n", "missing"),
    ],
)
def test_the_reader_refuses_what_it_does_not_understand(faulty: str, says: str) -> None:
    with pytest.raises(setup.SetupError) as refusal:
        setup.parse_choices(faulty)
    assert says in str(refusal.value)


def test_the_reader_does_not_pretend_to_be_yaml(plugin_root: Path, answers) -> None:
    """An anchor is not honoured, it is read as the text it is. The shape is flat, and a
    file that needs more than a flat shape is a file the harness will not half-understand."""
    read = setup.parse_choices(
        setup.format_choices(
            setup.read_answers(__import__("json").dumps(answers), plugin_root)
        ).replace("project_name: scratch", "project_name: &anchor scratch")
    )
    assert read["project_name"] == "&anchor scratch"


def test_the_reader_reads_what_the_writer_writes(plugin_root: Path, answers) -> None:
    answers["check_command"] = "make check --verbose"  # spaces and dashes survive
    read = setup.read_answers(__import__("json").dumps(answers), plugin_root)
    document = "# a comment\n\n" + setup.format_choices(read)
    assert setup.parse_choices(document)["check_command"] == "make check --verbose"


@pytest.mark.parametrize(
    "change, says",
    [
        ({"sets": ["git", "nope"]}, "no such set"),
        ({"profiles": ["anything"]}, "no such profile"),
        ({"features": ["anything"]}, "no such feature"),
        ({"sets": []}, "no rule set was chosen"),
        ({"decision_model": "elsewhere"}, "the backends are"),
        ({"project_name": "  "}, "project_name"),
        ({"check_command": ""}, "check_command"),
        ({"canary": ""}, "needs a canary word"),
        ({"sets": ["git"], "canary": "Word!"}, "read by nothing"),
        ({"nonsense": "x"}, "does not ask for"),
        ({"sets": "git"}, "must be a list"),
    ],
)
def test_an_answer_the_harness_cannot_honour_is_refused(
    plugin_root: Path, answers, change: dict, says: str
) -> None:
    answers.update(change)
    with pytest.raises(setup.SetupError) as refusal:
        setup.read_answers(__import__("json").dumps(answers), plugin_root)
    assert says in str(refusal.value)


def test_an_adoption_of_a_path_the_harness_does_not_own_is_refused(
    plugin_root: Path, answers
) -> None:
    answers["approvals"]["adopt"] = ["README.md"]
    with pytest.raises(setup.SetupError) as refusal:
        setup.read_answers(__import__("json").dumps(answers), plugin_root)
    assert "not a path the harness owns" in str(refusal.value)


def test_a_refusal_writes_nothing(project: Path, answers, setup_run) -> None:
    answers["sets"] = ["git", "nope"]
    code, said = setup_run("write", project, answers)
    assert code == 1 and "no such set" in said
    assert list(project.iterdir()) == []
