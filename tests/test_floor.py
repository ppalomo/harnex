"""The permission floor: what it covers, how it merges, and what it says it cannot do.

The floor exists because a hook cannot promise what it cannot deliver: when the guard's
hook itself fails, the host carries on with its normal permission flow, and what is in
the project's own permission file is all that is left. So the checks here are about
coverage and about not touching what is the project's.

Verified against Claude Code 2.1.269, whose documented rule order is deny, then ask, then
allow, with no exception carved out by a more specific allow.
"""

import json
from pathlib import Path

import pytest

import setup
from conftest import tree

GUARD = "guard"


def _floor(plugin_root: Path) -> dict:
    return json.loads((plugin_root / "control" / "floor.json").read_text(encoding="utf-8"))


def _guard_enforced_rules(rules_dir: Path) -> list[str]:
    import render_rules

    return sorted(
        rule.id
        for rules in render_rules.load_sets(rules_dir).values()
        for rule in rules
        if rule.enforced_by == GUARD
    )


def _uncovered(floor: dict, rules: list[str]) -> list[str]:
    """A rule the guard enforces with neither a floor entry nor a recorded reason."""
    covered = {entry["rule"] for entry in floor["entries"]}
    excused = {note["rule"] for note in floor["guard_only"]}
    return [rule for rule in rules if rule not in covered and rule not in excused]


def test_every_rule_the_guard_enforces_is_covered(plugin_root: Path, rules_dir: Path) -> None:
    uncovered = _uncovered(_floor(plugin_root), _guard_enforced_rules(rules_dir))
    assert not uncovered, (
        f"{uncovered} declare guard enforcement, and the floor neither carries an entry for "
        "them nor records why the host's syntax cannot express it"
    )


def test_the_coverage_check_fails_when_an_entry_goes_missing(
    plugin_root: Path, rules_dir: Path
) -> None:
    floor = _floor(plugin_root)
    floor["entries"] = [e for e in floor["entries"] if e["rule"] != "pushes-ask"]
    assert _uncovered(floor, _guard_enforced_rules(rules_dir)) == ["pushes-ask"]


def test_every_note_names_a_rule_that_exists(plugin_root: Path, rules_dir: Path) -> None:
    import render_rules

    known = {
        rule.id for rules in render_rules.load_sets(rules_dir).values() for rule in rules
    }
    floor = _floor(plugin_root)
    for entry in floor["entries"] + floor["guard_only"]:
        assert entry["rule"] in known, f"{entry['rule']} is not a rule the harness states"


def test_the_entries_are_scoped_and_well_formed(plugin_root: Path) -> None:
    for entry in _floor(plugin_root)["entries"]:
        pattern = entry["pattern"]
        assert entry["list"] in ("deny", "ask")
        assert pattern.endswith(")") and "(" in pattern, (
            f"{pattern} is a bare tool name: in deny that removes the tool from the model's "
            "context entirely, which is not what a floor is for"
        )
        tool, spec = setup._split_rule(pattern)
        assert tool and spec and spec != "*", f"{pattern} is not scoped"


def test_a_negation_comes_after_what_it_carves_out(plugin_root: Path) -> None:
    """The host reads a `!` pattern as carving out of the entries listed before it."""
    patterns = [e["pattern"] for e in _floor(plugin_root)["entries"]]
    for index, pattern in enumerate(patterns):
        if "(!" in pattern:
            assert index > 0 and any("(!" not in p for p in patterns[:index]), (
                f"{pattern} carves nothing out: it is listed before every rule it would"
            )


def test_the_floor_lands_in_a_project_with_no_settings(
    project: Path, plugin_root: Path, answers, setup_run
) -> None:
    setup_run("write", project, answers)
    settings = json.loads((project / setup.SETTINGS).read_text(encoding="utf-8"))
    for entry in _floor(plugin_root)["entries"]:
        assert entry["pattern"] in settings["permissions"][entry["list"]]


def test_the_merge_keeps_every_entry_the_project_had(project: Path, answers, setup_run) -> None:
    own = {
        "permissions": {
            "allow": ["Bash(ls *)"],
            "deny": ["Read(./secret.txt)"],
            "ask": ["Bash(make deploy *)"],
        },
        "env": {"MY_VAR": "1"},
        "hooks": {"Stop": []},
    }
    (project / ".claude").mkdir()
    (project / setup.SETTINGS).write_text(json.dumps(own, indent=2) + "\n", encoding="utf-8")

    code, _ = setup_run("write", project, answers)
    assert code == 0
    merged = json.loads((project / setup.SETTINGS).read_text(encoding="utf-8"))
    assert merged["env"] == own["env"]
    assert merged["hooks"] == own["hooks"]
    assert merged["permissions"]["allow"] == own["permissions"]["allow"]
    assert merged["permissions"]["deny"][0] == "Read(./secret.txt)"
    assert "Bash(make deploy *)" in merged["permissions"]["ask"]


def test_merging_again_writes_nothing(project: Path, answers, setup_run) -> None:
    setup_run("write", project, answers)
    before = tree(project)
    setup_run("write", project, answers)
    assert tree(project) == before


def test_an_entry_the_project_already_had_is_not_claimed_or_duplicated(
    project: Path, answers, setup_run
) -> None:
    (project / ".claude").mkdir()
    (project / setup.SETTINGS).write_text(
        json.dumps({"permissions": {"ask": ["Bash(git push *)"]}}, indent=2) + "\n",
        encoding="utf-8",
    )
    setup_run("write", project, answers)
    settings = json.loads((project / setup.SETTINGS).read_text(encoding="utf-8"))
    assert settings["permissions"]["ask"].count("Bash(git push *)") == 1

    record = json.loads((project / setup.MANIFEST).read_text(encoding="utf-8"))
    owned = record["entries"][setup.SETTINGS]["ask"]
    assert "Bash(git push *)" not in owned, "the harness claimed an entry the project wrote"


def test_a_settings_file_that_cannot_be_read_stops_the_run(
    project: Path, answers, setup_run
) -> None:
    (project / ".claude").mkdir()
    (project / setup.SETTINGS).write_text("{not json", encoding="utf-8")
    before = tree(project)
    code, said = setup_run("write", project, answers)
    assert code == 1
    assert "cannot be read as JSON" in said
    assert tree(project) == before


@pytest.mark.parametrize(
    "allow, reported",
    [
        ("Bash(git *)", True),
        ("Bash", True),
        ("Bash(*)", True),
        ("Bash(git push *)", True),
        ("Bash(git push:*)", True),
        ("Bash(make build *)", False),
        ("Read(./src/**)", False),
    ],
)
def test_an_allow_that_meets_the_floor_is_reported_and_never_stops_the_run(
    project: Path, answers, setup_run, allow: str, reported: bool
) -> None:
    (project / ".claude").mkdir()
    (project / setup.SETTINGS).write_text(
        json.dumps({"permissions": {"allow": [allow]}}, indent=2) + "\n", encoding="utf-8"
    )
    code, said = setup_run("plan", project, answers)
    assert code == 0, "an overlap is a notice, not a conflict: the host's order settles it"
    assert (f"`{allow}`" in said) is reported
    if reported:
        assert "deny, then ask, then allow" in said


def test_a_mode_that_bypasses_permissions_is_warned_about(
    project: Path, answers, setup_run
) -> None:
    (project / ".claude").mkdir()
    (project / setup.SETTINGS).write_text(
        json.dumps({"permissions": {"defaultMode": "bypassPermissions"}}, indent=2) + "\n",
        encoding="utf-8",
    )
    code, said = setup_run("write", project, answers)
    assert code == 0
    assert "bypasses permissions" in said and "No harness can defend against it" in said


@pytest.mark.parametrize(
    "allow, floor_pattern, meets",
    [
        ("Bash(git *)", "Bash(git push *)", True),
        ("Bash(git push *)", "Bash(git push *)", True),
        ("Bash(git:*)", "Bash(git push *)", True),
        ("Bash(git log *)", "Bash(git push *)", False),
        ("Read(**)", "Bash(rm *)", False),
        ("Bash", "Bash(rm *)", True),
    ],
)
def test_what_counts_as_meeting_a_floor_entry(allow: str, floor_pattern: str, meets: bool) -> None:
    assert setup.meets(allow, floor_pattern) is meets
