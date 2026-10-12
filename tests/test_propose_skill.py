"""`/harnex:propose` consults the project's own advisors once, between the proposal and
`design.md`, and the architect writes `design.md` from their briefs, naming the advisor
a section comes from (`agent-teams`, design.md D4, `architect-commands`). The skill is
prose a model follows with no other context, so what is checked is that the prose says
each thing the requirement needs, in the words that carry the contract: the list command
and its phase, where the consultation sits, one start per advisor and no write, the
named brief, the missing-agent remedy, the no-advisor case, and the verifier still once.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ARTIFACTS_STEP = "## 5."
CONSULT_STEP = "### Consult the project's advisors"
FOLD_STEP = "### Fold the briefs into `design.md`"
SCOPE_STEP = "## 6."
VERIFIER_STEP = "## 7."
FINISH_STEP = "## 8."


@pytest.fixture(scope="module")
def propose_text(plugin_root: Path) -> str:
    return (plugin_root / "skills" / "propose" / "SKILL.md").read_text(encoding="utf-8")


def _section(text: str, start: str, end: str) -> str:
    """The text between two headings, whitespace collapsed for substring checks."""
    begin = text.index(start)
    return " ".join(text[begin : text.index(end, begin)].split())


@pytest.fixture(scope="module")
def artifacts_step(propose_text: str) -> str:
    return _section(propose_text, ARTIFACTS_STEP, SCOPE_STEP)


@pytest.fixture(scope="module")
def consult_step(propose_text: str) -> str:
    return _section(propose_text, CONSULT_STEP, FOLD_STEP)


@pytest.fixture(scope="module")
def fold_step(propose_text: str) -> str:
    return _section(propose_text, FOLD_STEP, SCOPE_STEP)


@pytest.fixture(scope="module")
def verifier_step(propose_text: str) -> str:
    return _section(propose_text, VERIFIER_STEP, FINISH_STEP)


def test_the_consultation_sits_inside_the_artifacts_step_after_the_proposal_and_before_the_design(
    propose_text: str, artifacts_step: str
) -> None:
    """The sub-step is part of writing the artifacts (step 5), after the generic loop,
    before the design is folded, and before the scope check and the verifier."""
    assert (
        propose_text.index(ARTIFACTS_STEP)
        < propose_text.index(CONSULT_STEP)
        < propose_text.index(FOLD_STEP)
        < propose_text.index(SCOPE_STEP)
        < propose_text.index(VERIFIER_STEP)
    )
    assert "after `proposal.md` exists and before `design.md` is written" in artifacts_step
    assert "applies exactly once per run" in artifacts_step
    # The generic artifact loop still comes first, and the consultation is in its text order.
    assert artifacts_step.index("openspec instructions") < artifacts_step.index(
        "Consult the project's advisors"
    )


def test_the_consultation_lists_the_propose_phase_agents_with_the_renderer(consult_step: str) -> None:
    """The list is the one source of who to start and how to name them (D7): the skill
    runs `render_agents.py list` for the `propose` phase and never reads an agent's body."""
    assert 'uv run "${CLAUDE_PLUGIN_ROOT}/scripts/render_agents.py" list' in consult_step
    assert "--phase propose" in consult_step
    assert "--profiles" in consult_step
    assert "Never read an agent's body" in consult_step


def test_the_consultation_reads_the_profiles_the_store_step_reads(consult_step: str) -> None:
    assert "`.harnex/config.yml`" in consult_step
    assert "`.harnex.yml`" in consult_step


def test_a_project_without_advisors_proceeds_exactly_as_before(consult_step: str) -> None:
    """No profiles, an empty list, or a list that prints nothing: the sub-step is skipped
    and the command is what it was before this capability existed."""
    assert "skip this whole sub-step" in consult_step
    assert "proceeds exactly as before this capability existed" in consult_step
    assert "If it prints nothing, skip the rest of this sub-step" in consult_step


def test_a_missing_agent_is_reported_with_update_as_the_remedy(consult_step: str) -> None:
    assert "`.claude/agents/<name>.md` exists" in consult_step
    assert "the agent is missing" in consult_step
    assert "`/harnex:update` as the remedy" in consult_step
    assert "go on with the others" in consult_step
    assert "Never render or write the agent here" in consult_step


def test_each_advisor_starts_once_with_the_proposal_and_writes_nothing(consult_step: str) -> None:
    assert "`subagent_type: <name>`" in consult_step
    assert "Start each agent that exists once" in consult_step
    assert "path of `proposal.md`" in consult_step
    assert "with no `model` override" in consult_step
    assert "an advisor is read-only, it writes nothing" in consult_step
    assert "never asked to write an artifact" in consult_step
    assert "never start an advisor a second time" in consult_step
    assert "Wait for every brief you can obtain before writing `design.md`" in consult_step


def test_the_architect_writes_the_design_and_names_the_advisor_a_section_comes_from(
    fold_step: str,
) -> None:
    """The brief is the architect's input, not an artifact: the design is written by the
    main session, and a section taken from a brief carries the advisor's own list line."""
    assert "Each brief is your own input, not a section to paste" in fold_step
    assert "names the advisor it came from" in fold_step
    assert "the emoji, one space, the `name`" in fold_step
    assert "whose brief a section comes from" in fold_step
    assert "Where two advisors disagree, the call is yours" in fold_step
    assert "the advisors are not consulted again in this run" in fold_step


def test_the_verifier_still_runs_once_at_the_end(propose_text: str, verifier_step: str) -> None:
    assert "## 7. Start the verifier once, and show its review" in propose_text
    assert "`subagent_type: verifier`" in verifier_step
    assert "still runs exactly once, here, at the end" in verifier_step
    assert "the advisors of step 5 do not replace it" in verifier_step
    assert "- Call the verifier more than once per run" in propose_text


def test_the_never_does_list_covers_the_advisors(propose_text: str) -> None:
    assert "- Start an advisor more than once per run" in propose_text
    assert "consult an advisor after `design.md` exists" in propose_text
    assert "- Let an advisor write an artifact" in propose_text
    assert "- Render or write an agent" in propose_text
    assert "`/harnex:update` as the remedy" in propose_text
