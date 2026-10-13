"""What a project is asked, and what the harness refuses to be told.

Two shapes meet here: the answers document the session hands the script, which is JSON
because a session writes it, and the project's own record of those answers, which is a
flat file because every later hook and command reads it. The reader of that flat file is
the schema: what it does not understand, it refuses, with the line.
"""

import json
from pathlib import Path

import pytest

import render_agents
import setup


def test_the_choices_come_from_what_the_harness_holds(plugin_root: Path) -> None:
    on_offer = setup.choices_on_offer(plugin_root)
    assert on_offer["sets"] == setup.available_sets(plugin_root)
    assert on_offer["decision_models"] == list(setup.DECISION_BACKENDS)
    assert on_offer["default_canary"]


def test_the_choices_offer_the_specialists_by_department_beside_the_teams(
    plugin_root: Path,
) -> None:
    """`choices` prints `specialists`, what a roster can name, grouped by department, each
    with its emoji and phase; `teams` is still there and unchanged (design.md D6)."""
    on_offer = setup.choices_on_offer(plugin_root)
    specialists = on_offer["specialists"]
    assert list(specialists) == list(render_agents.DEPARTMENTS)
    names = {
        department: [member["specialist"] for member in members]
        for department, members in specialists.items()
    }
    assert names == {
        "design": ["accessibility-reviewer", "designer"],
        "engineering": ["api-designer", "migration-reviewer", "security-reviewer"],
    }
    held = render_agents.held_specialists(plugin_root)
    for department, members in specialists.items():
        assert members == [
            {"specialist": e["specialist"], "emoji": e["emoji"], "phase": e["phase"]}
            for e in held
            if e["department"] == department
        ]
        for member in members:
            assert len(member["emoji"]) == 1
            assert member["phase"] in render_agents.FRAGMENT_PHASES
    assert on_offer["teams"] == setup.available_teams(plugin_root)


def test_a_kind_of_choice_with_nothing_to_choose_from(tmp_path: Path, plugin_root: Path) -> None:
    """Profile documents and features are both discovered from the harness itself."""
    assert setup.available_profiles(plugin_root) == ["fastapi", "flutter", "rails", "react"]
    assert setup.available_features(plugin_root) == []

    holding = tmp_path / "plugin"
    (holding / "tools" / "profiles" / "one").mkdir(parents=True)
    (holding / "tools" / "profiles" / "two").mkdir(parents=True)
    (holding / "tools" / "features.json").write_text('[{"name": "guard"}]', encoding="utf-8")
    assert setup.available_profiles(holding) == ["one", "two"]
    assert setup.available_features(holding) == ["guard"]


def test_a_directory_profile_reports_the_same_name_a_flat_one_did(plugin_root: Path) -> None:
    """`fastapi` moved from `fastapi.md` to `fastapi/profile.md` (agent-teams, design.md
    D1): a project that recorded `fastapi` still finds it on offer under that name."""
    profiles = plugin_root / "tools" / "profiles"
    assert (profiles / "fastapi" / "profile.md").is_file()
    assert not (profiles / "fastapi.md").exists()
    assert (profiles / "react.md").is_file(), "a flat profile is still a profile"
    assert "fastapi" in setup.available_profiles(plugin_root)


def test_flutter_is_on_offer_but_is_not_a_ui_profile(plugin_root: Path) -> None:
    """`ui.json` means "Playwright applies", and it does not for Flutter (agent-teams,
    design.md D6): the profile is on offer, and its `profile.md` says what evidence
    `verify` reads instead, but it is left out of the registry so no Playwright entry is
    ever proposed for it."""
    assert "flutter" in setup.available_profiles(plugin_root)
    assert "flutter" not in setup.ui_profiles(plugin_root)
    assert setup.ui_profiles(plugin_root) == ["react"], "the registry itself is unchanged"
    profile = plugin_root / "tools" / "profiles" / "flutter" / "profile.md"
    assert "## Verification evidence" in profile.read_text(encoding="utf-8")


def test_the_playwright_approval_is_per_run(plugin_root: Path, answers) -> None:
    assert not setup.read_answers(json.dumps(answers), plugin_root).mcp_playwright
    answers["approvals"]["mcp_playwright"] = True
    assert setup.read_answers(json.dumps(answers), plugin_root).mcp_playwright


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


def test_a_store_path_without_local_visibility_is_refused(plugin_root: Path, answers) -> None:
    answers["store_path"] = "/somewhere/store"
    with pytest.raises(setup.SetupError) as refusal:
        setup.read_answers(__import__("json").dumps(answers), plugin_root)
    assert "`store_path` is answered but `visibility` is not `local`" in str(refusal.value)


def test_a_store_path_must_be_text(plugin_root: Path, answers) -> None:
    answers["visibility"] = "local"
    answers["store_id"] = "scratch-store"
    answers["store_path"] = ["/somewhere/store"]
    with pytest.raises(setup.SetupError) as refusal:
        setup.read_answers(__import__("json").dumps(answers), plugin_root)
    assert "`store_path` must be text" in str(refusal.value)


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
    assert [p.name for p in project.iterdir()] == [".git"], "only the fixture's own repository"


def test_a_template_with_nothing_to_answer_it_fails_loudly(
    tmp_path: Path, plugin_root: Path
) -> None:
    """A token left in a project's file would be worse than a refusal: the project would
    carry a placeholder nobody notices."""
    templates = tmp_path / "plugin" / "context" / "templates"
    templates.mkdir(parents=True)
    (templates / "thing.md").write_text("# {{project_name}} and {{nobody}}\n", encoding="utf-8")
    with pytest.raises(setup.SetupError) as refusal:
        setup.render_template(tmp_path / "plugin", "thing.md", {"project_name": "a"})
    assert "nothing answers" in str(refusal.value)


def test_a_pointer_file_states_where_it_goes(tmp_path: Path, plugin_root: Path) -> None:
    for name in ("agents", "claude"):
        pointer = setup.load_pointer(plugin_root, name)
        assert pointer.position in ("top", "end")
        assert pointer.requires and pointer.without
        assert pointer.present_in(pointer.text)

    templates = tmp_path / "plugin" / "context" / "templates"
    templates.mkdir(parents=True)
    (templates / "pointer-nowhere.md").write_text("just a line\n", encoding="utf-8")
    with pytest.raises(setup.SetupError) as refusal:
        setup.load_pointer(tmp_path / "plugin", "nowhere")
    assert "position" in str(refusal.value)


# --- the roster (agent-roster, design.md D1) ------------------------------------------


def test_the_answers_document_carries_the_roster_or_leaves_it_absent(
    plugin_root: Path, answers
) -> None:
    absent = setup.read_answers(json.dumps(answers), plugin_root)
    assert absent.roster_recorded is False
    assert "team" not in absent.as_choices()

    answers["team"] = ["security-reviewer"]
    answers["bench"] = []
    recorded = setup.read_answers(json.dumps(answers), plugin_root)
    assert recorded.roster_recorded is True
    assert recorded.team == ("security-reviewer",)
    assert recorded.bench == ()


def test_the_answers_document_refuses_one_roster_key_without_the_other(
    plugin_root: Path, answers
) -> None:
    answers["team"] = ["reviewer"]
    with pytest.raises(setup.SetupError) as refusal:
        setup.read_answers(json.dumps(answers), plugin_root)
    assert "`bench`" in str(refusal.value)


def test_the_roster_is_kept_out_of_the_required_keys() -> None:
    for key in setup.ROSTER_KEYS:
        assert key not in setup.ANSWER_KEYS
        assert key not in setup.LOCAL_ANSWER_KEYS
        assert key not in setup.LIST_KEYS
        assert key not in setup.LOCAL_LIST_KEYS


def _keys_in_order(text: str) -> list[str]:
    return [line.split(":", 1)[0] for line in text.splitlines() if line and not line.startswith(" ")]


@pytest.mark.parametrize(
    "team, bench",
    [(("reviewer", "verifier"), ("debugger",)), ((), ())],
    ids=["named", "nobody"],
)
def test_a_recorded_roster_is_written_once_and_last_in_either_shape(
    team: tuple, bench: tuple
) -> None:
    answers = setup.Answers(
        project_name="scratch",
        profiles=("fastapi",),
        sets=("code",),
        features=(),
        canary="",
        decision_model="mock",
        check_command="make check",
        visibility="local",
        store_id="scratch-store",
        team=team,
        bench=bench,
        roster_recorded=True,
    )
    shared = setup.format_choices(answers)
    local = setup.format_local_choices(answers)

    assert _keys_in_order(shared) == list(setup.ANSWER_KEYS) + list(setup.ROSTER_KEYS)
    assert _keys_in_order(local) == list(setup.LOCAL_ANSWER_KEYS) + list(setup.ROSTER_KEYS)

    read_shared = setup.parse_choices(shared)
    read_local = setup.parse_choices(
        local, setup.LOCAL_CHOICES, setup.LOCAL_ANSWER_KEYS, setup.LOCAL_LIST_KEYS
    )
    assert read_shared == answers.as_choices()
    assert read_local == answers.as_local_choices()
    assert setup.read_roster(read_shared) == (team, bench)
    assert setup.read_roster(read_local, setup.LOCAL_CHOICES) == (team, bench)


def test_an_absent_roster_is_not_written(plugin_root: Path, answers) -> None:
    read = setup.read_answers(json.dumps(answers), plugin_root)
    written = setup.format_choices(read)
    assert _keys_in_order(written) == list(setup.ANSWER_KEYS)
    assert setup.read_roster(setup.parse_choices(written)) is None


# --- a roster is validated (agent-roster, design.md D2) -------------------------------


def _renderer_refusal(team: list[str], bench: list[str], plugin_root: Path) -> str:
    """What the renderer itself says of a roster, so setup is held to the same words."""
    with pytest.raises(render_agents.AgentError) as refusal:
        render_agents._check_roster(team, bench, plugin_root)
    return str(refusal.value)


@pytest.mark.parametrize(
    "team, bench, says",
    [
        (["nobody-at-all"], [], "it names no role the harness holds"),
        (["builder"], [], "its phase is `apply`"),
        ([], ["verifier"], "its phase is `verify`"),
        (["debugger"], [], "it ships as a plugin agent"),
        (["security-reviewer"], ["security-reviewer"], "named on both the team and the bench"),
    ],
    ids=["unknown", "apply-phase", "verify-phase", "shipped-adapter", "both-lists"],
)
def test_a_roster_naming_anything_but_a_held_specialist_is_refused_before_any_plan(
    project: Path, plugin_root: Path, answers, setup_run, team: list, bench: list, says: str
) -> None:
    answers["team"] = team
    answers["bench"] = bench
    expected = _renderer_refusal(team, bench, plugin_root)
    assert says in expected
    held = [entry["specialist"] for entry in render_agents.held_specialists(plugin_root)]
    assert "The specialists held are: " + ", ".join(held) + "." in expected

    with pytest.raises(setup.SetupError) as refusal:
        setup.read_answers(json.dumps(answers), plugin_root)
    assert str(refusal.value) == expected

    code, said = setup_run("plan", project, answers)
    assert code == 1
    assert expected in said
    assert [p.name for p in project.iterdir()] == [".git"], "only the fixture's own repository"


def test_a_roster_of_held_specialists_is_accepted(plugin_root: Path, answers) -> None:
    answers["team"] = ["security-reviewer"]
    answers["bench"] = ["designer"]
    read = setup.read_answers(json.dumps(answers), plugin_root)
    assert (read.team, read.bench) == (("security-reviewer",), ("designer",))
