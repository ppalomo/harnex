"""`/harnex:review` fans out to the project's own reviewers after the core one, and shows
every review as returned (`agent-teams`, design.md D4, `review-command`). The skill is
prose a model follows with no other context, so what is checked is that the prose says
each thing the requirement needs, in the words that carry the contract: the list command
and its phase, the missing-agent remedy, the label, no merge, and the core reviewer's
fixed model staying the core reviewer's alone.
"""

from __future__ import annotations

from pathlib import Path

import pytest

CORE_STEP = "## 3."
TEAM_STEP = "## 4."
FINISH_STEP = "## 5."


@pytest.fixture(scope="module")
def review_text(plugin_root: Path) -> str:
    return (plugin_root / "skills" / "review" / "SKILL.md").read_text(encoding="utf-8")


def _section(text: str, start: str, end: str) -> str:
    """The text between two step headings, whitespace collapsed for substring checks."""
    begin = text.index(start)
    return " ".join(text[begin : text.index(end, begin)].split())


@pytest.fixture(scope="module")
def core_step(review_text: str) -> str:
    return _section(review_text, CORE_STEP, TEAM_STEP)


@pytest.fixture(scope="module")
def team_step(review_text: str) -> str:
    return _section(review_text, TEAM_STEP, FINISH_STEP)


def test_the_team_step_follows_the_core_reviewer_and_precedes_finish(review_text: str) -> None:
    assert review_text.index(CORE_STEP) < review_text.index(TEAM_STEP) < review_text.index(FINISH_STEP)
    assert "## 4. Start the project's own reviewers, once each" in review_text
    assert "## 5. Finish" in review_text


def test_the_team_step_lists_the_review_phase_agents_with_the_renderer(team_step: str) -> None:
    """The list is the one source of who to start and how to label them (D7): the skill
    runs `render_agents.py list` for the `review` phase and never reads an agent's body."""
    assert 'uv run "${CLAUDE_PLUGIN_ROOT}/scripts/render_agents.py" list' in team_step
    assert "--phase review" in team_step
    assert "--profiles" in team_step
    assert "Never read an agent's body" in team_step


def test_the_team_step_reads_the_profiles_the_advice_line_reads(team_step: str) -> None:
    assert "`.harnex/config.yml`" in team_step
    assert "`.harnex.yml`" in team_step


def test_a_project_without_a_team_sees_exactly_what_it_saw_before(team_step: str) -> None:
    """No profiles, an empty list, or a list that prints nothing: the step is skipped, so
    the core reviewer's review is the whole review, as it was before this capability."""
    assert "skip this whole step" in team_step
    assert "exactly what it was before this capability existed" in team_step
    assert "If it prints nothing, skip the rest of this step" in team_step


def test_a_missing_agent_is_reported_with_update_as_the_remedy(team_step: str) -> None:
    assert "`.claude/agents/<name>.md` exists" in team_step
    assert "the agent is missing" in team_step
    assert "`/harnex:update` as the remedy" in team_step
    assert "go on with the others" in team_step
    assert "Never render or write the agent here" in team_step


def test_each_agent_starts_once_with_the_same_diff(team_step: str) -> None:
    assert "`subagent_type: <name>`" in team_step
    assert "Start each agent that exists once" in team_step
    assert "the same diff the core reviewer received" in team_step


def test_each_review_is_shown_as_returned_under_the_list_s_own_line(team_step: str) -> None:
    """The label is the list's line — emoji, one space, `name` — and the review under it
    is the agent's own words, after the core reviewer's and in the list's order."""
    assert "exactly as it comes back" in team_step
    assert "after the core reviewer's review" in team_step
    assert "in the list's order" in team_step
    assert "the list's own line for that agent" in team_step
    assert "the emoji, one space, the `name`, nothing else" in team_step


def test_reviews_are_never_merged(review_text: str, team_step: str) -> None:
    assert "Never merge two reviews into one" in team_step
    assert "never drop a finding because another reviewer reported it" in team_step
    assert "never summarise" in team_step
    assert "- Merge, dedupe or summarise reviews" in review_text


def test_the_fixed_model_belongs_to_the_core_reviewer_alone(
    review_text: str, core_step: str, team_step: str
) -> None:
    """`model: opus` is set where the core reviewer is started and nowhere else; the
    stack reviewers are started with no model override, and the skill says so."""
    assert "always setting `model: opus`" in core_step
    assert "with no `model` override" in team_step
    assert "belongs to the core reviewer alone" in team_step
    assert "- Override a stack reviewer's model" in review_text
    # Every mention of the fixed model outside step 3 says whose it is, never sets it.
    for mention in _mentions(review_text, "`model: opus`"):
        assert "always setting" in mention or "core reviewer" in mention, mention


def _mentions(text: str, needle: str, span: int = 80) -> list[str]:
    """Each occurrence of `needle` with its surrounding text, whitespace collapsed."""
    found, start = [], 0
    while (at := text.find(needle, start)) != -1:
        found.append(" ".join(text[max(0, at - span) : at + len(needle) + span].split()))
        start = at + len(needle)
    return found


def test_the_never_does_list_covers_every_reviewer(review_text: str) -> None:
    assert "- Call any reviewer, core or stack, more than once per run." in review_text
    assert "- Render or write an agent" in review_text
