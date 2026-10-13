"""`/harnex:setup` says what a profile's team brings and reports the agents it wrote;
`/harnex:update` names the rendered agents among what it refreshes and removes
(`agent-teams`, design.md D3 and D7, `project-setup` and `harness-update`). Both skills
are prose a model follows with no other context, so what is checked is that the prose
says each thing the requirement needs, in the words that carry the contract: the `teams`
key and its `<emoji> <specialist>` shape, the agent paths exempted from the clean-tree
check one by one and never the directory, the `remove` line inside the one plan, and the
`Removed:` line in each report.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _collapsed(text: str) -> str:
    """Whitespace collapsed, so a check does not depend on where a line wraps."""
    return " ".join(text.split())


def _between(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    return _collapsed(text[begin : text.index(end, begin)])


@pytest.fixture(scope="module")
def setup_text(plugin_root: Path) -> str:
    return (plugin_root / "skills" / "setup" / "SKILL.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def update_text(plugin_root: Path) -> str:
    return (plugin_root / "skills" / "update" / "SKILL.md").read_text(encoding="utf-8")


# --- setup ------------------------------------------------------------------------------


def test_setup_exempts_each_agent_path_from_the_clean_tree_check_but_not_the_directory(
    setup_text: str,
) -> None:
    """D3: the rendered agent paths join the harness's own paths one by one, from the
    profiles and from the record, so a stale agent never blocks the run that removes it;
    `.claude/agents/` itself stays the project's."""
    check = _between(setup_text, "git status --porcelain=v1", 'setup.py" choices')
    own = check[check.index("The harness's own paths do not count") :]
    assert "`.claude/agents/<profile>-<specialist>.md`" in own
    assert "generic `.claude/agents/<specialist>.md`" in own
    assert "the roster (`team` and `bench`) and the profiles" in own
    assert "the generation record lists" in own
    assert "each path on its own" in own
    assert "a stale agent awaiting removal never blocks the run that removes it" in own
    assert "never the directory `.claude/agents/` itself nor any other file in it" in own
    assert "an uncommitted one counts like any other project path" in own
    # The exemption is stated inside the list, before the rerun it exists for.
    assert own.index("`.claude/agents/<profile>-<specialist>.md`") < own.index(
        "a rerun before the person commits what setup wrote"
    )


def test_setup_says_what_a_profile_s_team_brings_when_offering_it(setup_text: str) -> None:
    """The offer reads `choices`' `teams` key and shows each specialist as the emoji, one
    space, the name (D7); an empty team brings none, and who is on the project's team is
    the roster's answer, not the profile's."""
    item = _between(setup_text, "**Profiles**", "**Canary word**")
    assert "say which specialists its team brings" in item
    assert "read from the `teams` key of `choices`" in item
    assert "`specialist`, `emoji` and `phase`" in item
    assert "read it as JSON, since the raw output escapes the emoji" in item
    assert "`<emoji> <specialist>`: the emoji, exactly one space, the name" in item
    assert "A profile with an empty list brings none" in item
    assert "Choosing the profile imports its team" not in item
    assert "who is on the project's team is the roster's answer, asked next" in item


def test_setup_asks_the_roster_after_the_profiles_and_before_the_canary_word(
    setup_text: str,
) -> None:
    """D6: the roster question sits between the profiles and the canary word, on a first
    setup only."""
    ask = _between(setup_text, "## 2. Ask", "## 3. Local visibility")
    assert ask.index("**Profiles**") < ask.index("**Roster**") < ask.index("**Canary word**")
    assert "**Roster** — on a first setup only" in ask
    # The roster is longer than 4, so the batching rule names it with the rule sets.
    assert "A list longer than 4 — the rule sets, the roster — is a multi-select" in ask


def test_setup_s_roster_question_groups_by_department_and_proposes_the_profiles_specialists(
    setup_text: str,
) -> None:
    item = _between(setup_text, "**Roster**", "**Canary word**")
    assert "every specialist from the `specialists` key of `choices`" in item
    assert "grouped by department" in item
    assert "engineering, then design" in item
    assert "each as `<emoji> <name>` with its phase" in item
    assert (
        "Propose as the team every specialist the chosen profiles hold a fragment for, "
        "read from `teams`, and an empty bench" in item
    )
    assert "Record both lists in the answers document, `team` and `bench`" in item


def test_setup_never_asks_the_roster_of_a_project_whose_choices_are_recorded(
    setup_text: str,
) -> None:
    item = _between(setup_text, "**Roster**", "**Canary word**")
    assert "A project whose choices are recorded is never asked this again" in item
    assert "the person edits the file and runs setup again to change it" in item
    learn = _between(setup_text, "Then look for the project's already-recorded answers", "## 2.")
    assert "do not ask again, visibility and roster included" in learn


def test_setup_forwards_team_and_bench_on_a_rerun_only_when_recorded(setup_text: str) -> None:
    """D1: an absent roster stays absent, never an empty one."""
    plan = _between(setup_text, "## 4. Show the plan", "## 5. Approvals")
    assert '"team": ["…"], "bench": []' in plan
    assert (
        "On a rerun, copy `team` and `bench` from the recorded choices file into the "
        "answers document only when the file carries them" in plan
    )
    assert "leave both keys out — never write either as an empty list" in plan
    assert "an absent roster stays absent" in plan


def test_setup_s_one_plan_lists_each_agent_and_may_list_a_remove_line(setup_text: str) -> None:
    """The agent lines and the `remove` line sit inside the one plan the person approves
    with a single yes — that yes is what covers the deletion (D3)."""
    plan = _between(setup_text, "## 4. Show the plan", "## 5. Approvals")
    assert "single yes to it covers them. There is no second plan." in plan
    assert "one line per rendered agent under `.claude/agents/`" in plan
    assert "naming the profile it comes from" in plan
    assert "With a roster, each line's detail names" in plan
    assert "a `remove` line for an agent the record lists but a dropped profile no longer renders" in plan
    assert "that line is part of the one plan" in plan
    assert "single yes to the plan is what covers that deletion" in plan
    assert "ask for no separate yes" in plan
    assert "remove nothing the plan did not list" in plan
    # A conflict on an agent path is resolved like any other, adoption only for a rendered one.
    assert "A `conflict` on an agent path is resolved like any other" in plan
    assert "adoption, only for a path the roster and the chosen profiles render, not the profiles alone" in plan
    assert "An agent line may also be generic — `.claude/agents/<specialist>.md`" in plan
    assert "an edited stale agent is deleted by hand, or restored as the harness wrote it" in plan


def test_setup_s_report_names_the_agents_written_and_removed(setup_text: str) -> None:
    text = _collapsed(setup_text)
    report = text[text.index("every side effect beyond them, by name") :]
    assert "The agents written under `.claude/agents/`, each by its path" in report
    assert "when the script printed a `Removed:` line — the agents removed" in report


def test_setup_never_renders_an_agent_by_hand_or_removes_one_the_plan_did_not_list(
    setup_text: str,
) -> None:
    never = _collapsed(setup_text[setup_text.index("## What this skill never does") :])
    assert "Render or edit an agent by hand, or remove an agent the plan did not list" in never
    assert "a `remove` line is approved with the plan it sits in" in never


# --- update -----------------------------------------------------------------------------


def test_update_names_the_rendered_agents_among_what_it_refreshes(update_text: str) -> None:
    intro = _between(update_text, "# Updating a project", "## What this skill never does")
    assert "the rendered agents under `.claude/agents/`" in intro
    assert (
        "rewritten when the harness's own role or profile fragment changed and left "
        "byte-stable otherwise" in intro
    )


def test_update_removes_a_dropped_profile_s_agents_asking_nothing(update_text: str) -> None:
    """The removal needs no question: the file's own reason — everything in an update plan
    was already approved when the project ran setup — covers it (D3)."""
    intro = _between(update_text, "# Updating a project", "## What this skill never does")
    assert "an agent the record lists that a dropped profile no longer renders is removed" in intro
    assert "It asks no question" in intro
    assert "the removal included, since everything in an update plan was already approved" in intro
    run = _between(update_text, "## 1. Run it", "## 2. Present the report")
    assert "everything in an update plan was already approved when the project ran setup" in run


def test_update_s_report_carries_the_removed_line(update_text: str) -> None:
    report = _collapsed(update_text[update_text.index("## 2. Present the report") :])
    assert "**A `Removed:` line** — names each stale agent the run deleted, by path" in report
    assert "show it as printed, asking nothing" in report


def test_update_stops_on_an_agent_conflict_like_any_other(update_text: str) -> None:
    conflict = _collapsed(update_text[update_text.index("A conflict — a harness-owned file") :])
    assert "a conflict on an agent path stops the run like any other" in conflict
    assert "update itself never adopts one" in conflict


def test_update_re_renders_from_the_recorded_roster_and_profiles(update_text: str) -> None:
    intro = _between(update_text, "# Updating a project", "## What this skill never does")
    assert "Update re-renders from the recorded roster and profiles" in intro
    assert (
        "A name added to or removed from the roster takes effect on the next update" in intro
    )
    assert "A dropped profile turns a prefixed agent into the generic one" in intro
    assert "`.claude/agents/<specialist>.md`" in intro


def test_update_never_adds_a_roster_to_the_choices_file(update_text: str) -> None:
    never = _between(update_text, "## What this skill never does", "## 1. Run it")
    assert "Update never adds `team` or `bench` to `.harnex.yml`" in never
    assert "a roster is recorded only by `/harnex:setup`" in never
