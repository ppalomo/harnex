"""A chosen list of profiles renders one set of agents, and always the same one.

`setup` writes each rendered agent into a project and records its hash; `update`
overwrites it while that hash still matches. That only works if the bytes are a function
of the project's choices and of the harness's own content — not of the clock, not of the
plugin's version, not of the order the profiles were typed in. Those are the properties
checked here, along with the two refusals that keep a team honest: a fragment that names
no role is not skipped, and a fragment for a role that writes or binds a verdict is never
turned into a stack agent.

The fixtures build a harness of their own under `tmp_path` — four roles, one per phase,
and a few profiles — so nothing here depends on which stacks the plugin ships. One check
renders the real roles against a fixture profile directory, and one section per shipped
team reads the profile directories the plugin does ship, since a typo in one of their
file names would otherwise reach every project that chose the profile.

The plugin's own adapters are the same rendering without a profile, written by `sync`
(design.md D8); the checks of `sync` build their adapters under the fixture harness too.
That the shipped adapters are clean is asserted once, by the correspondence test in
`test_agent_and_skill_frontmatter.py`, not repeated here.
"""

import os
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest
import render_agents
from render_agents import AgentError

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "plugin" / "scripts" / "render_agents.py"

READ_ONLY = "Read, Grep, Glob"
WRITING = "Read, Grep, Glob, Edit, Write, Bash"


def _role(name: str, emoji: str, phase: str, tools: str) -> str:
    return f"""\
---
name: {name}
description: {emoji} Does the {name}'s work in the {phase} phase. Read-only where it can be.
tools: {tools}
phase: {phase}
department: engineering
---

# {name}

You do the {name}'s work. The one constraint that defines you is stated here.

## Who you are

{emoji} **Someone** — careful: you say "I am not sure" before you say "this is wrong".

## Procedure

Read first, then report. The stack section below says what to look at.
"""


ROLES = {
    "checker": _role("checker", "\U0001f50d", "review", READ_ONLY),
    "adviser": _role("adviser", "\U0001f9ed", "propose", READ_ONLY),
    "maker": _role("maker", "\U0001f528", "apply", WRITING),
    "judge": _role("judge", "⚖", "verify", READ_ONLY),
}

PROFILES = {
    "alpha/profile.md": "# alpha\n\nThe alpha stack.\n",
    "alpha/checker.md": "On alpha, look at the first thing.\n\nThen the second.\n",
    "alpha/adviser.md": "On alpha, advise about the layout.\n",
    "beta/profile.md": "# beta\n\nThe beta stack.\n",
    "beta/checker.md": "On beta, look at the third thing.\n",
    "gamma.md": "# gamma\n\nA stack with no team.\n",
}


@pytest.fixture
def harness(tmp_path: Path) -> Path:
    """A plugin root holding one role per phase and three profiles."""
    root = tmp_path / "plugin"
    for name, text in ROLES.items():
        path = root / "orchestration" / "roles" / f"{name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    for relative, text in PROFILES.items():
        path = root / "tools" / "profiles" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _fragment(harness: Path, profile: str, specialist: str) -> Path:
    path = harness / "tools" / "profiles" / profile / f"{specialist}.md"
    path.write_text(f"On {profile}, for {specialist}.\n", encoding="utf-8")
    return path


def _frontmatter(content: bytes) -> tuple[dict[str, str], str]:
    text = content.decode("utf-8")
    assert text.startswith("---\n")
    head, body = text[4:].split("\n---\n", 1)
    fields = dict(line.split(": ", 1) for line in head.split("\n"))
    return fields, body


# --- a pure function of the choices --------------------------------------------------


def test_the_order_asked_for_does_not_reach_the_bytes(harness: Path) -> None:
    assert render_agents.render(["alpha", "beta"], harness) == render_agents.render(
        ["beta", "alpha"], harness
    )


def test_the_same_choice_renders_the_same_bytes(harness: Path) -> None:
    assert render_agents.render(["alpha"], harness) == render_agents.render(
        ["alpha"], harness
    )


def test_a_repeated_profile_renders_once(harness: Path) -> None:
    assert render_agents.render(["alpha", "alpha"], harness) == render_agents.render(
        ["alpha"], harness
    )


def test_the_map_is_sorted_by_path(harness: Path) -> None:
    paths = list(render_agents.render(["beta", "alpha"], harness))
    assert paths == sorted(paths)
    assert paths == [
        ".claude/agents/alpha-adviser.md",
        ".claude/agents/alpha-checker.md",
        ".claude/agents/beta-checker.md",
    ]


def test_a_single_file_profile_renders_nothing(harness: Path) -> None:
    assert render_agents.render(["gamma"], harness) == {}
    assert render_agents.fragments_of("gamma", harness / "tools" / "profiles") == {}


def test_a_profile_with_no_fragments_renders_nothing(harness: Path) -> None:
    (harness / "tools" / "profiles" / "delta").mkdir()
    (harness / "tools" / "profiles" / "delta" / "profile.md").write_text("# delta\n")
    assert render_agents.render(["delta"], harness) == {}


def test_only_the_chosen_profiles_are_rendered(harness: Path) -> None:
    assert list(render_agents.render(["beta", "gamma"], harness)) == [
        ".claude/agents/beta-checker.md"
    ]


# --- the refusals -------------------------------------------------------------------


def test_a_fragment_naming_no_role_is_refused_with_the_roles_held(harness: Path) -> None:
    stray = _fragment(harness, "alpha", "nobody")
    with pytest.raises(AgentError) as refusal:
        render_agents.render(["alpha"], harness)
    message = str(refusal.value)
    assert str(stray) in message
    assert "adviser, checker, judge, maker" in message


def test_a_fragment_for_an_apply_phase_role_is_refused(harness: Path) -> None:
    stray = _fragment(harness, "beta", "maker")
    with pytest.raises(AgentError) as refusal:
        render_agents.render(["beta"], harness)
    message = str(refusal.value)
    assert str(stray) in message
    assert "apply-phase" in message
    assert "only a review- or propose-phase role takes a fragment" in message


def test_a_fragment_for_a_verify_phase_role_is_refused(harness: Path) -> None:
    stray = _fragment(harness, "beta", "judge")
    with pytest.raises(AgentError) as refusal:
        render_agents.render(["beta"], harness)
    message = str(refusal.value)
    assert str(stray) in message
    assert "verify-phase" in message
    assert "only a review- or propose-phase role takes a fragment" in message


def test_a_refusal_in_one_profile_renders_nothing_for_any(harness: Path) -> None:
    """Nothing is returned until every fragment is accepted, so a partial team cannot
    reach a project."""
    _fragment(harness, "beta", "maker")
    with pytest.raises(AgentError):
        render_agents.render(["alpha", "beta"], harness)


def test_an_unknown_profile_is_refused(harness: Path) -> None:
    with pytest.raises(AgentError, match="no such profile: nope"):
        render_agents.render(["nope"], harness)


# --- what a rendered agent holds ----------------------------------------------------


def test_a_rendered_agent_has_exactly_the_minimum_agent_fields(harness: Path) -> None:
    agents = render_agents.render(["alpha"], harness)
    fields, _ = _frontmatter(agents[".claude/agents/alpha-checker.md"])
    assert list(fields) == ["name", "description", "tools"]
    assert "phase" not in fields


def test_a_rendered_agent_is_named_after_profile_and_specialist(harness: Path) -> None:
    agents = render_agents.render(["alpha"], harness)
    fields, _ = _frontmatter(agents[".claude/agents/alpha-checker.md"])
    assert fields["name"] == "alpha-checker"


def test_a_rendered_agent_keeps_the_role_tools_and_names_no_writing_tool(
    harness: Path,
) -> None:
    agents = render_agents.render(["alpha", "beta"], harness)
    for content in agents.values():
        fields, _ = _frontmatter(content)
        assert fields["tools"] == READ_ONLY
        for tool in ("Edit", "Write", "Bash"):
            assert tool not in fields["tools"].split(", ")


def test_the_description_is_the_role_description_suffixed_with_the_profile(
    harness: Path,
) -> None:
    role = render_agents.read_role(harness / "orchestration" / "roles" / "checker.md")
    agents = render_agents.render(["alpha"], harness)
    fields, _ = _frontmatter(agents[".claude/agents/alpha-checker.md"])
    assert fields["description"] == f"{role.description} — stack: alpha"
    assert fields["description"][0] == role.description[0]
    assert unicodedata.category(fields["description"][0]) == "So"


def test_the_body_opens_with_the_role_and_ends_with_the_fragment(harness: Path) -> None:
    role = render_agents.read_role(harness / "orchestration" / "roles" / "checker.md")
    agents = render_agents.render(["alpha"], harness)
    _, body = _frontmatter(agents[".claude/agents/alpha-checker.md"])
    assert body.startswith(role.body.rstrip() + "\n")
    assert body.endswith(
        "\n## For this stack: alpha\n\n"
        "On alpha, look at the first thing.\n\nThen the second.\n"
    )
    assert not body.endswith("\n\n")


def test_each_profile_gets_its_own_fragment(harness: Path) -> None:
    agents = render_agents.render(["alpha", "beta"], harness)
    _, alpha = _frontmatter(agents[".claude/agents/alpha-checker.md"])
    _, beta = _frontmatter(agents[".claude/agents/beta-checker.md"])
    assert "## For this stack: beta" in beta and "third thing" in beta
    assert "beta" not in alpha


def test_a_role_file_is_read_whole(harness: Path) -> None:
    role = render_agents.read_role(harness / "orchestration" / "roles" / "maker.md")
    assert (role.name, role.phase, role.tools) == ("maker", "apply", WRITING)
    assert role.body.lstrip().startswith("# maker\n")


def test_a_role_missing_a_field_is_refused(harness: Path) -> None:
    path = harness / "orchestration" / "roles" / "checker.md"
    path.write_text(ROLES["checker"].replace("phase: review\n", ""), encoding="utf-8")
    with pytest.raises(AgentError, match="declares no phase"):
        render_agents.render(["alpha"], harness)


def test_a_role_with_an_unknown_department_is_refused_by_name(harness: Path) -> None:
    path = harness / "orchestration" / "roles" / "checker.md"
    path.write_text(
        ROLES["checker"].replace("department: engineering\n", "department: marketing\n"),
        encoding="utf-8",
    )
    with pytest.raises(AgentError, match="department `marketing`, which is none of "
                       "engineering, design"):
        render_agents.read_role(path)


def test_a_rendered_agent_carries_no_department(harness: Path) -> None:
    for content in render_agents.render(["alpha"], harness).values():
        fields, _ = _frontmatter(content)
        assert "department" not in fields and "phase" not in fields


# --- the real roles -----------------------------------------------------------------


def test_the_real_roles_render_against_a_fixture_profile(
    plugin_root: Path, tmp_path: Path
) -> None:
    """The plugin's own roles, with a team built here so no shipped profile is needed."""
    profiles = tmp_path / "profiles"
    team = profiles / "omega"
    team.mkdir(parents=True)
    (team / "profile.md").write_text("# omega\n", encoding="utf-8")
    for specialist in ("designer", "security-reviewer", "api-designer"):
        (team / f"{specialist}.md").write_text(f"On omega, as {specialist}.\n")

    agents = render_agents.render(["omega"], plugin_root, profiles)

    assert list(agents) == [
        ".claude/agents/omega-api-designer.md",
        ".claude/agents/omega-designer.md",
        ".claude/agents/omega-security-reviewer.md",
    ]
    for relative, content in agents.items():
        fields, body = _frontmatter(content)
        specialist = relative.removeprefix(".claude/agents/omega-").removesuffix(".md")
        role = render_agents.read_role(
            plugin_root / "orchestration" / "roles" / f"{specialist}.md"
        )
        assert list(fields) == ["name", "description", "tools"]
        assert fields["name"] == f"omega-{specialist}"
        assert fields["tools"] == role.tools == READ_ONLY
        assert fields["description"][0] == role.description[0]
        assert body.startswith(role.body.rstrip() + "\n")
        assert body.endswith(f"## For this stack: omega\n\nOn omega, as {specialist}.\n")


@pytest.mark.parametrize("specialist", ["builder", "test-engineer", "verifier"])
def test_the_real_writing_and_verifying_roles_take_no_fragment(
    plugin_root: Path, tmp_path: Path, specialist: str
) -> None:
    profiles = tmp_path / "profiles"
    team = profiles / "omega"
    team.mkdir(parents=True)
    (team / "profile.md").write_text("# omega\n", encoding="utf-8")
    (team / f"{specialist}.md").write_text("Never.\n", encoding="utf-8")

    with pytest.raises(AgentError, match="only a review- or propose-phase role"):
        render_agents.render(["omega"], plugin_root, profiles)


# --- the shipped fastapi team ---------------------------------------------------------

FASTAPI_TEAM = ("api-designer", "migration-reviewer", "security-reviewer")


def test_the_fastapi_profile_renders_its_three_specialists(plugin_root: Path) -> None:
    """`fastapi/` is a directory profile: `profile.md` plus one fragment per specialist,
    rendered against the real roles, with the role's body whole and the fragment last."""
    agents = render_agents.render(["fastapi"], plugin_root)

    assert list(agents) == [f".claude/agents/fastapi-{s}.md" for s in FASTAPI_TEAM]
    profile = plugin_root / "tools" / "profiles" / "fastapi"
    for specialist in FASTAPI_TEAM:
        fields, body = _frontmatter(agents[f".claude/agents/fastapi-{specialist}.md"])
        role = render_agents.read_role(
            plugin_root / "orchestration" / "roles" / f"{specialist}.md"
        )
        fragment = (profile / f"{specialist}.md").read_text(encoding="utf-8")
        assert list(fields) == ["name", "description", "tools"]
        assert fields["name"] == f"fastapi-{specialist}"
        assert fields["tools"] == role.tools == READ_ONLY
        assert fields["description"] == f"{role.description} — stack: fastapi"
        assert body.startswith(role.body.rstrip() + "\n")
        assert body.endswith("\n## For this stack: fastapi\n\n" + fragment.strip() + "\n")
        assert not fragment.startswith("---"), "a fragment carries no frontmatter"


def test_the_fastapi_team_is_split_by_phase(plugin_root: Path) -> None:
    review = render_agents.agents_for(["fastapi"], "review", plugin_root)
    assert [agent.name for agent in review] == [
        "fastapi-migration-reviewer",
        "fastapi-security-reviewer",
    ]
    propose = render_agents.agents_for(["fastapi"], "propose", plugin_root)
    assert [agent.name for agent in propose] == ["fastapi-api-designer"]
    for phase in ("apply", "verify"):
        assert render_agents.agents_for(["fastapi"], phase, plugin_root) == []


# --- the shipped rails team -----------------------------------------------------------

RAILS_TEAM = ("api-designer", "migration-reviewer", "security-reviewer")


def test_the_rails_profile_renders_its_three_specialists(plugin_root: Path) -> None:
    """`rails/` is the second directory profile, with the same three specialists as
    `fastapi/`, rendered against the same real roles."""
    agents = render_agents.render(["rails"], plugin_root)

    assert list(agents) == [f".claude/agents/rails-{s}.md" for s in RAILS_TEAM]
    profile = plugin_root / "tools" / "profiles" / "rails"
    for specialist in RAILS_TEAM:
        fields, body = _frontmatter(agents[f".claude/agents/rails-{specialist}.md"])
        role = render_agents.read_role(
            plugin_root / "orchestration" / "roles" / f"{specialist}.md"
        )
        fragment = (profile / f"{specialist}.md").read_text(encoding="utf-8")
        assert list(fields) == ["name", "description", "tools"]
        assert fields["name"] == f"rails-{specialist}"
        assert fields["tools"] == role.tools == READ_ONLY
        assert fields["description"] == f"{role.description} — stack: rails"
        assert body.startswith(role.body.rstrip() + "\n")
        assert body.endswith("\n## For this stack: rails\n\n" + fragment.strip() + "\n")
        assert not fragment.startswith("---"), "a fragment carries no frontmatter"


def test_the_rails_team_is_split_by_phase(plugin_root: Path) -> None:
    review = render_agents.agents_for(["rails"], "review", plugin_root)
    assert [agent.name for agent in review] == [
        "rails-migration-reviewer",
        "rails-security-reviewer",
    ]
    propose = render_agents.agents_for(["rails"], "propose", plugin_root)
    assert [agent.name for agent in propose] == ["rails-api-designer"]
    for phase in ("apply", "verify"):
        assert render_agents.agents_for(["rails"], phase, plugin_root) == []


def test_the_fastapi_and_rails_teams_render_side_by_side(plugin_root: Path) -> None:
    """Two shipped profiles with the same three specialists give six agents, each named
    after its own profile, so neither team's file overwrites the other's."""
    agents = render_agents.render(["fastapi", "rails"], plugin_root)

    assert len(agents) == 6
    assert list(agents) == [f".claude/agents/fastapi-{s}.md" for s in FASTAPI_TEAM] + [
        f".claude/agents/rails-{s}.md" for s in RAILS_TEAM
    ]
    names = [_frontmatter(content)[0]["name"] for content in agents.values()]
    assert len(set(names)) == 6


# --- the shipped flutter team ---------------------------------------------------------

FLUTTER_TEAM = ("accessibility-reviewer", "designer", "security-reviewer")


def test_the_flutter_profile_renders_its_three_specialists(plugin_root: Path) -> None:
    """`flutter/` is the third directory profile, and the first whose team is a UI one:
    a designer and an accessibility reviewer beside the security reviewer, rendered
    against the same real roles."""
    agents = render_agents.render(["flutter"], plugin_root)

    assert list(agents) == [f".claude/agents/flutter-{s}.md" for s in FLUTTER_TEAM]
    profile = plugin_root / "tools" / "profiles" / "flutter"
    for specialist in FLUTTER_TEAM:
        fields, body = _frontmatter(agents[f".claude/agents/flutter-{specialist}.md"])
        role = render_agents.read_role(
            plugin_root / "orchestration" / "roles" / f"{specialist}.md"
        )
        fragment = (profile / f"{specialist}.md").read_text(encoding="utf-8")
        assert list(fields) == ["name", "description", "tools"]
        assert fields["name"] == f"flutter-{specialist}"
        assert fields["tools"] == role.tools == READ_ONLY
        assert fields["description"] == f"{role.description} — stack: flutter"
        assert body.startswith(role.body.rstrip() + "\n")
        assert body.endswith("\n## For this stack: flutter\n\n" + fragment.strip() + "\n")
        assert not fragment.startswith("---"), "a fragment carries no frontmatter"


def test_the_flutter_team_is_split_by_phase(plugin_root: Path) -> None:
    review = render_agents.agents_for(["flutter"], "review", plugin_root)
    assert [agent.name for agent in review] == [
        "flutter-accessibility-reviewer",
        "flutter-security-reviewer",
    ]
    propose = render_agents.agents_for(["flutter"], "propose", plugin_root)
    assert [agent.name for agent in propose] == ["flutter-designer"]
    for phase in ("apply", "verify"):
        assert render_agents.agents_for(["flutter"], phase, plugin_root) == []


def test_the_three_shipped_teams_render_side_by_side(plugin_root: Path) -> None:
    """All three shipped profiles give nine agents with nine distinct names, so no
    team's file overwrites another's — including the two that share a specialist."""
    agents = render_agents.render(["fastapi", "flutter", "rails"], plugin_root)

    assert len(agents) == 9
    assert list(agents) == (
        [f".claude/agents/fastapi-{s}.md" for s in FASTAPI_TEAM]
        + [f".claude/agents/flutter-{s}.md" for s in FLUTTER_TEAM]
        + [f".claude/agents/rails-{s}.md" for s in RAILS_TEAM]
    )
    names = [_frontmatter(content)[0]["name"] for content in agents.values()]
    assert len(set(names)) == 9


# --- the command line ---------------------------------------------------------------


def _run(harness: Path, command: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), command, "--plugin-root", str(harness), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_command_line_lists_the_paths(harness: Path) -> None:
    result = _run(harness, "render", "--profiles", "beta,alpha")
    assert result.returncode == 0
    assert result.stdout.split("\n")[:-1] == list(render_agents.render(["alpha", "beta"], harness))


def test_the_command_line_writes_the_same_bytes(harness: Path, tmp_path: Path) -> None:
    project = tmp_path / "project"
    result = _run(harness, "render", "--profiles", "alpha", "--out-dir", str(project))
    assert result.returncode == 0
    for relative, content in render_agents.render(["alpha"], harness).items():
        assert (project / relative).read_bytes() == content


def test_a_refusal_on_the_command_line_writes_nothing(harness: Path, tmp_path: Path) -> None:
    _fragment(harness, "alpha", "maker")
    project = tmp_path / "project"
    result = _run(harness, "render", "--profiles", "alpha", "--out-dir", str(project))
    assert result.returncode == 2
    assert "only a review- or propose-phase role takes a fragment" in result.stderr
    assert not project.exists(), "a refused rendering left files behind"


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ([], ["render", "list"]),
        (["render"], ["--profiles", "--plugin-root", "--out-dir"]),
        (["list"], ["--profiles", "--plugin-root", "--phase", "apply,propose,review,verify"]),
    ],
)
def test_the_command_line_explains_itself(arguments: list[str], expected: list[str]) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *arguments, "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    for text in expected:
        assert text in result.stdout


# --- which agents a phase starts -----------------------------------------------------


def _roles(harness: Path) -> dict[str, render_agents.Role]:
    return {
        name: render_agents.read_role(harness / "orchestration" / "roles" / f"{name}.md")
        for name in ROLES
    }


def test_phase_of_reads_the_role_phase(harness: Path) -> None:
    roles = _roles(harness)
    assert {name: render_agents.phase_of(role) for name, role in roles.items()} == {
        "checker": "review",
        "adviser": "propose",
        "maker": "apply",
        "judge": "verify",
    }


def test_phase_of_refuses_a_phase_that_is_none_of_the_four(harness: Path) -> None:
    path = harness / "orchestration" / "roles" / "checker.md"
    path.write_text(ROLES["checker"].replace("phase: review\n", "phase: later\n"))
    with pytest.raises(AgentError, match="`later`, which is none of apply, propose, review, verify"):
        render_agents.phase_of(render_agents.read_role(path))
    with pytest.raises(AgentError, match="`later`, which is none of"):
        render_agents.render(["alpha"], harness)


def test_review_lists_only_the_review_phase_agents(harness: Path) -> None:
    agents = render_agents.agents_for(["alpha", "beta"], "review", harness)
    assert [agent.name for agent in agents] == ["alpha-checker", "beta-checker"]
    assert {agent.role for agent in agents} == {"checker"}
    assert {agent.phase for agent in agents} == {"review"}
    assert [agent.path for agent in agents] == [
        ".claude/agents/alpha-checker.md",
        ".claude/agents/beta-checker.md",
    ]


def test_propose_lists_only_the_propose_phase_agents(harness: Path) -> None:
    agents = render_agents.agents_for(["alpha", "beta"], "propose", harness)
    assert [(agent.name, agent.role, agent.phase) for agent in agents] == [
        ("alpha-adviser", "adviser", "propose")
    ]


def test_apply_lists_nothing(harness: Path) -> None:
    assert render_agents.agents_for(["alpha", "beta"], "apply", harness) == []


def test_verify_lists_nothing(harness: Path) -> None:
    assert render_agents.agents_for(["alpha", "beta"], "verify", harness) == []


def test_an_unknown_phase_is_refused(harness: Path) -> None:
    with pytest.raises(AgentError, match="no such phase: ship"):
        render_agents.agents_for(["alpha"], "ship", harness)


def test_the_emoji_is_the_first_code_point_of_the_rendered_description(
    harness: Path,
) -> None:
    roles = _roles(harness)
    rendered = render_agents.render(["alpha", "beta"], harness)
    for phase in ("review", "propose"):
        for agent in render_agents.agents_for(["alpha", "beta"], phase, harness):
            fields, _ = _frontmatter(rendered[agent.path])
            assert len(agent.emoji) == 1
            assert unicodedata.category(agent.emoji) == "So"
            assert agent.emoji == fields["description"][0]
            assert agent.emoji == roles[agent.role].description[0]


def test_the_list_is_sorted_by_name_whatever_the_profile_order(harness: Path) -> None:
    forward = render_agents.agents_for(["alpha", "beta"], "review", harness)
    backward = render_agents.agents_for(["beta", "alpha"], "review", harness)
    assert forward == backward
    assert [agent.name for agent in forward] == sorted(agent.name for agent in forward)


def test_a_flat_profile_contributes_no_agent(harness: Path) -> None:
    for phase in render_agents.PHASES:
        assert render_agents.agents_for(["gamma"], phase, harness) == []
    assert render_agents.agents_for(["gamma", "beta"], "review", harness) == (
        render_agents.agents_for(["beta"], "review", harness)
    )


def test_agents_for_refuses_whatever_render_refuses(harness: Path) -> None:
    """A stray fragment in one profile is refused by every phase's listing, including a
    phase it does not belong to, so a skill never fans out over a team setup would not
    have written."""
    _fragment(harness, "beta", "maker")
    for phase in render_agents.PHASES:
        with pytest.raises(AgentError, match="only a review- or propose-phase role"):
            render_agents.agents_for(["alpha", "beta"], phase, harness)
    with pytest.raises(AgentError, match="no such profile: nope"):
        render_agents.agents_for(["nope"], "review", harness)


def test_the_command_line_prints_emoji_and_name_per_agent(harness: Path) -> None:
    result = _run(harness, "list", "--profiles", "beta,alpha", "--phase", "review")
    assert result.returncode == 0
    assert result.stdout == "\U0001f50d alpha-checker\n\U0001f50d beta-checker\n"
    assert result.stderr == ""

    result = _run(harness, "list", "--profiles", "alpha", "--phase", "propose")
    assert result.returncode == 0
    assert result.stdout == "\U0001f9ed alpha-adviser\n"


def test_the_command_line_prints_nothing_for_a_project_with_no_team(harness: Path) -> None:
    for phase in render_agents.PHASES:
        result = _run(harness, "list", "--profiles", "gamma", "--phase", phase)
        assert result.returncode == 0
        assert result.stdout == ""
        assert result.stderr == ""


def test_the_command_line_refuses_a_phase_that_is_none_of_the_four(harness: Path) -> None:
    result = _run(harness, "list", "--profiles", "alpha", "--phase", "ship")
    assert result.returncode == 2
    assert result.stdout == ""
    assert "invalid choice: 'ship'" in result.stderr


def test_the_real_roles_are_listed_by_phase(plugin_root: Path, tmp_path: Path) -> None:
    profiles = tmp_path / "profiles"
    team = profiles / "omega"
    team.mkdir(parents=True)
    (team / "profile.md").write_text("# omega\n", encoding="utf-8")
    for specialist in ("designer", "security-reviewer", "api-designer"):
        (team / f"{specialist}.md").write_text(f"On omega, as {specialist}.\n")

    def emoji(role: str) -> str:
        path = plugin_root / "orchestration" / "roles" / f"{role}.md"
        return render_agents.read_role(path).description[0]

    review = render_agents.agents_for(["omega"], "review", plugin_root, profiles)
    assert [(agent.name, agent.emoji) for agent in review] == [
        ("omega-security-reviewer", emoji("security-reviewer")),
    ]
    assert [agent.emoji for agent in review] == ["\U0001f510"]

    propose = render_agents.agents_for(["omega"], "propose", plugin_root, profiles)
    assert [(agent.name, agent.emoji) for agent in propose] == [
        ("omega-api-designer", emoji("api-designer")),
        ("omega-designer", emoji("designer")),
    ]
    assert [agent.emoji for agent in propose] == ["\U0001f50c", "\U0001f3a8"]

    for phase in ("apply", "verify"):
        assert render_agents.agents_for(["omega"], phase, plugin_root, profiles) == []


# --- the plugin's own adapters (design.md D8) -----------------------------------------


def _adapter(harness: Path, name: str, content: bytes | None = None) -> Path:
    """An adapter under the fixture harness's `agents/`: the rendering of its role unless
    other bytes are given, so a check can start clean or dirty by choice."""
    path = harness / "agents" / f"{name}.md"
    path.parent.mkdir(exist_ok=True)
    if content is None:
        content = render_agents.adapter_of(_roles(harness)[name])
    path.write_bytes(content)
    return path


def _clean(harness: Path, *names: str) -> dict[str, Path]:
    return {name: _adapter(harness, name) for name in names}


def test_the_adapter_is_the_role_without_its_phase(harness: Path) -> None:
    """Three fields copied verbatim, no `phase`, the body whole — whatever the phase,
    since the apply- and verify-phase roles are core agents too."""
    for name, role in _roles(harness).items():
        fields, body = _frontmatter(render_agents.adapter_of(role))
        assert fields == {
            "name": role.name,
            "description": role.description,
            "tools": role.tools,
        }
        assert body == role.body.rstrip() + "\n"
        assert body.strip() == role.body.strip()


def test_sync_rewrites_a_differing_adapter_and_names_it(harness: Path) -> None:
    paths = _clean(harness, "checker", "maker")
    paths["maker"].write_text("---\nname: maker\n---\n\nAn old copy.\n", encoding="utf-8")

    assert render_agents.sync(harness) == ["maker"]
    assert paths["maker"].read_bytes() == render_agents.adapter_of(_roles(harness)["maker"])
    assert paths["checker"].read_bytes() == render_agents.adapter_of(_roles(harness)["checker"])


def test_check_on_a_clean_tree_reports_nothing_and_writes_nothing(harness: Path) -> None:
    paths = _clean(harness, "checker", "judge")
    before = {name: (path.read_bytes(), os.stat(path).st_mtime_ns) for name, path in paths.items()}

    assert render_agents.sync(harness, check=True) == []
    assert render_agents.sync(harness) == []
    assert {name: (path.read_bytes(), os.stat(path).st_mtime_ns) for name, path in paths.items()} == before


def test_check_on_a_dirty_adapter_names_it_and_leaves_it(harness: Path) -> None:
    paths = _clean(harness, "checker", "adviser")
    dirty = b"---\nname: adviser\n---\n\nEdited by hand.\n"
    paths["adviser"].write_bytes(dirty)

    assert render_agents.sync(harness, check=True) == ["adviser"]
    assert paths["adviser"].read_bytes() == dirty

    result = _run(harness, "sync", "--check")
    assert result.returncode == 1
    assert result.stdout == "stale adviser\n"
    assert result.stderr == ""
    assert paths["adviser"].read_bytes() == dirty


def test_an_adapter_with_no_role_is_refused_by_name(harness: Path) -> None:
    """Refused, not skipped, and nothing else is written either: a stale adapter beside
    the stray one stays stale until the stray one is dealt with."""
    paths = _clean(harness, "checker")
    paths["checker"].write_bytes(b"")
    stray = _adapter(harness, "nobody", b"---\nname: nobody\n---\n\nNo such role.\n")

    with pytest.raises(AgentError, match=r"nobody\.md: binds no role") as refusal:
        render_agents.sync(harness)
    assert "checker" in str(refusal.value)
    assert paths["checker"].read_bytes() == b""

    for arguments in ((), ("--check",)):
        result = _run(harness, "sync", *arguments)
        assert result.returncode == 2
        assert result.stdout == ""
        assert result.stderr.startswith("render_agents: ")
        assert str(stray) in result.stderr
    assert paths["checker"].read_bytes() == b""


def test_an_empty_adapter_file_is_filled(harness: Path) -> None:
    """How a core agent is added: an empty file of the role's name, then `sync`."""
    path = _adapter(harness, "judge", b"")

    assert render_agents.sync(harness, check=True) == ["judge"]
    assert path.read_bytes() == b""
    assert render_agents.sync(harness) == ["judge"]
    assert path.read_bytes() == render_agents.adapter_of(_roles(harness)["judge"])


def test_sync_twice_changes_nothing(harness: Path) -> None:
    _adapter(harness, "checker", b"")
    _adapter(harness, "maker", b"stale")
    assert render_agents.sync(harness) == ["checker", "maker"]
    after_first = {path: path.read_bytes() for path in (harness / "agents").glob("*.md")}

    assert render_agents.sync(harness) == []
    assert render_agents.sync(harness, check=True) == []
    assert {path: path.read_bytes() for path in (harness / "agents").glob("*.md")} == after_first


def test_the_command_line_names_what_it_synced(harness: Path) -> None:
    _clean(harness, "checker")
    _adapter(harness, "adviser", b"")
    _adapter(harness, "maker", b"")

    result = _run(harness, "sync")
    assert result.returncode == 0
    assert result.stdout == "synced adviser\nsynced maker\n"
    assert result.stderr == ""

    result = _run(harness, "sync")
    assert result.returncode == 0
    assert result.stdout == ""
    result = _run(harness, "sync", "--check")
    assert result.returncode == 0
    assert result.stdout == ""


def test_a_harness_with_no_agents_directory_is_refused(harness: Path) -> None:
    with pytest.raises(AgentError, match="is not a directory of agents"):
        render_agents.sync(harness)


# --- the specialists a roster can name --------------------------------------------------


def test_the_shipped_plugin_holds_five_specialists(plugin_root: Path) -> None:
    """A specialist is a review- or propose-phase role that does not ship as a plugin
    agent: `debugger` is a review role but has an adapter under `agents/`, and `builder`
    is left out by its phase, `apply`."""
    specialists = render_agents.held_specialists(plugin_root)

    assert [(s["department"], s["specialist"]) for s in specialists] == [
        ("design", "accessibility-reviewer"),
        ("design", "designer"),
        ("engineering", "api-designer"),
        ("engineering", "migration-reviewer"),
        ("engineering", "security-reviewer"),
    ]
    names = {s["specialist"] for s in specialists}
    assert "debugger" not in names
    assert (plugin_root / "agents" / "debugger.md").is_file()
    assert "builder" not in names
    for entry in specialists:
        assert set(entry) == {"specialist", "department", "emoji", "phase"}
        assert entry["phase"] in ("review", "propose")
        role = render_agents.read_role(
            plugin_root / "orchestration" / "roles" / f"{entry['specialist']}.md"
        )
        assert entry["emoji"] == role.description[0]


# --- the roster (design.md D2, D3 of `agent-roster`) -------------------------------------


def _omega(tmp_path: Path, *specialists: str) -> Path:
    """A profiles directory holding one team, `omega`, with a fragment per name given."""
    profiles = tmp_path / "profiles"
    team = profiles / "omega"
    team.mkdir(parents=True)
    (team / "profile.md").write_text("# omega\n", encoding="utf-8")
    for specialist in specialists:
        (team / f"{specialist}.md").write_text(f"On omega, as {specialist}.\n")
    return profiles


def test_a_roster_name_with_no_fragment_renders_the_generic_agent(harness: Path) -> None:
    """`beta` holds no fragment for `adviser`, so the roster's `adviser` is the role's
    adapter at the project path; `beta-checker` is off the roster and renders nothing."""
    agents = render_agents.render(["beta"], harness, team=["adviser"], bench=[])

    assert list(agents) == [".claude/agents/adviser.md"]
    assert agents[".claude/agents/adviser.md"] == render_agents.adapter_of(
        _roles(harness)["adviser"]
    )
    assert render_agents.render_generic(_roles(harness)["adviser"]) == (
        render_agents.adapter_of(_roles(harness)["adviser"])
    )


def test_a_roster_name_with_a_fragment_in_one_profile_renders_the_prefixed_agent_only(
    harness: Path,
) -> None:
    agents = render_agents.render(["beta"], harness, team=["checker"], bench=[])
    assert agents == {
        ".claude/agents/beta-checker.md": render_agents.render(["beta"], harness)[
            ".claude/agents/beta-checker.md"
        ]
    }


def test_a_roster_name_with_fragments_in_two_profiles_renders_two_prefixed_agents(
    harness: Path,
) -> None:
    agents = render_agents.render(["alpha", "beta"], harness, team=["checker"], bench=[])
    assert list(agents) == [
        ".claude/agents/alpha-checker.md",
        ".claude/agents/beta-checker.md",
    ]


def test_a_fragment_for_a_name_off_the_roster_renders_nothing(harness: Path) -> None:
    agents = render_agents.render(["alpha"], harness, team=["checker"], bench=[])
    assert ".claude/agents/alpha-adviser.md" not in agents
    assert list(agents) == [".claude/agents/alpha-checker.md"]


@pytest.mark.parametrize(
    ("specialist", "expected"),
    [
        ("maker", "only a review- or propose-phase role takes a fragment"),
        ("judge", "only a review- or propose-phase role takes a fragment"),
        ("nobody", "names no role the harness holds"),
    ],
)
def test_an_invalid_fragment_off_the_roster_is_still_refused(
    harness: Path, specialist: str, expected: str
) -> None:
    stray = _fragment(harness, "beta", specialist)
    with pytest.raises(AgentError) as refusal:
        render_agents.render(["beta"], harness, team=["checker"], bench=[])
    assert str(stray) in str(refusal.value)
    assert expected in str(refusal.value)


@pytest.mark.parametrize("roster", [None, (["security-reviewer"], [])])
def test_a_fragment_for_a_role_that_ships_as_a_plugin_agent_is_refused_by_name(
    plugin_root: Path, tmp_path: Path, roster: tuple[list[str], list[str]] | None
) -> None:
    profiles = _omega(tmp_path, "debugger", "security-reviewer")
    team, bench = roster if roster else (None, None)
    with pytest.raises(AgentError) as refusal:
        render_agents.render(["omega"], plugin_root, profiles, team=team, bench=bench)
    message = str(refusal.value)
    assert str(profiles / "omega" / "debugger.md") in message
    assert "`debugger` ships as a plugin agent" in message


def test_no_shipped_profile_carries_a_fragment_for_a_role_that_ships(
    plugin_root: Path,
) -> None:
    shipped = {path.stem for path in (plugin_root / "agents").glob("*.md")}
    profiles = plugin_root / "tools" / "profiles"
    for directory in sorted(path for path in profiles.iterdir() if path.is_dir()):
        assert not shipped & set(render_agents.fragments_of(directory.name, profiles))


def test_an_empty_roster_renders_nothing(harness: Path) -> None:
    assert render_agents.render(["alpha", "beta"], harness, team=[], bench=[]) == {}
    for phase in render_agents.PHASES:
        assert render_agents.agents_for(["alpha"], phase, harness, team=[], bench=[]) == []


def test_the_same_roster_in_two_orders_renders_the_same_bytes(harness: Path) -> None:
    forward = render_agents.render(
        ["alpha", "beta"], harness, team=["checker", "adviser"], bench=[]
    )
    backward = render_agents.render(
        ["beta", "alpha"], harness, team=["adviser", "checker", "adviser"], bench=[]
    )
    assert forward == backward
    assert list(forward) == sorted(forward)


def test_a_bench_name_is_rendered_and_never_listed(harness: Path) -> None:
    agents = render_agents.render(["beta"], harness, team=["checker"], bench=["adviser"])
    assert ".claude/agents/adviser.md" in agents

    for phase in render_agents.PHASES:
        listed = render_agents.agents_for(
            ["beta"], phase, harness, team=["checker"], bench=["adviser"]
        )
        assert "adviser" not in {agent.role for agent in listed}
    review = render_agents.agents_for(
        ["beta"], "review", harness, team=["checker"], bench=["adviser"]
    )
    assert [agent.name for agent in review] == ["beta-checker"]


def test_a_generic_team_agent_is_listed_under_its_own_name(harness: Path) -> None:
    propose = render_agents.agents_for(["beta"], "propose", harness, team=["adviser"], bench=[])
    assert [(agent.name, agent.path, agent.emoji) for agent in propose] == [
        ("adviser", ".claude/agents/adviser.md", "\U0001f9ed")
    ]


def test_without_a_roster_the_walk_is_unchanged(harness: Path) -> None:
    """`C10`'s output: every fragment of every chosen profile, and no generic agent."""
    agents = render_agents.render(["alpha", "beta"], harness)
    assert agents == render_agents.render(["alpha", "beta"], harness, team=None, bench=None)
    assert list(agents) == [
        ".claude/agents/alpha-adviser.md",
        ".claude/agents/alpha-checker.md",
        ".claude/agents/beta-checker.md",
    ]
    assert [a.name for a in render_agents.agents_for(["alpha", "beta"], "review", harness)] == [
        "alpha-checker",
        "beta-checker",
    ]


@pytest.mark.parametrize(
    ("team", "bench", "missing"), [(["checker"], None, "bench"), (None, [], "team")]
)
def test_one_roster_list_without_the_other_is_refused(
    harness: Path, team: list[str] | None, bench: list[str] | None, missing: str
) -> None:
    with pytest.raises(AgentError, match=f"`{missing}` is missing"):
        render_agents.render(["alpha"], harness, team=team, bench=bench)
    with pytest.raises(AgentError, match=f"`{missing}` is missing"):
        render_agents.agents_for(["alpha"], "review", harness, team=team, bench=bench)


def test_roster_refusal_names_the_entry_the_reason_and_the_specialists(
    harness: Path,
) -> None:
    message = render_agents.roster_refusal(
        "nobody", "it names no role the harness holds", render_agents.held_specialists(harness)
    )
    assert message == (
        "`nobody` cannot be on a roster: it names no role the harness holds. "
        "The specialists held are: adviser, checker."
    )


@pytest.mark.parametrize(
    ("team", "bench", "entry", "reason"),
    [
        (["nobody"], [], "nobody", "it names no role the harness holds"),
        (
            ["maker"],
            [],
            "maker",
            "its phase is `apply`, and only a review- or propose-phase role can be "
            "on a roster",
        ),
        (
            [],
            ["judge"],
            "judge",
            "its phase is `verify`, and only a review- or propose-phase role can be "
            "on a roster",
        ),
        (["checker"], ["checker"], "checker", "it is named on both the team and the bench"),
    ],
)
def test_each_roster_refusal_is_worded_by_roster_refusal(
    harness: Path, team: list[str], bench: list[str], entry: str, reason: str
) -> None:
    expected = render_agents.roster_refusal(
        entry, reason, render_agents.held_specialists(harness)
    )
    assert "The specialists held are: adviser, checker." in expected
    with pytest.raises(AgentError) as refusal:
        render_agents.render(["alpha"], harness, team=team, bench=bench)
    assert str(refusal.value) == expected
    with pytest.raises(AgentError) as refusal:
        render_agents.agents_for(["alpha"], "review", harness, team=team, bench=bench)
    assert str(refusal.value) == expected


def test_a_roster_name_that_ships_as_a_plugin_agent_is_refused(harness: Path) -> None:
    """`checker` gains an adapter under `agents/`, so it is in every project already and
    no longer a specialist a roster can name."""
    _adapter(harness, "checker")
    expected = render_agents.roster_refusal(
        "checker",
        "it ships as a plugin agent, so every project has it already",
        render_agents.held_specialists(harness),
    )
    assert expected.endswith("The specialists held are: adviser.")
    with pytest.raises(AgentError) as refusal:
        render_agents.render(["gamma"], harness, team=["checker"], bench=[])
    assert str(refusal.value) == expected


def test_the_real_debugger_cannot_be_on_a_roster(plugin_root: Path, tmp_path: Path) -> None:
    profiles = _omega(tmp_path)
    with pytest.raises(AgentError) as refusal:
        render_agents.render(["omega"], plugin_root, profiles, team=["debugger"], bench=[])
    message = str(refusal.value)
    assert message.startswith("`debugger` cannot be on a roster: it ships as a plugin agent")
    assert message.endswith(
        "The specialists held are: accessibility-reviewer, designer, api-designer, "
        "migration-reviewer, security-reviewer."
    )


# --- the roster on the command line (design.md D5 of `agent-roster`) -------------------


def test_the_command_line_lists_the_team_and_not_the_bench(harness: Path) -> None:
    for phase, expected in (("review", "\U0001f50d beta-checker\n"), ("propose", "")):
        result = _run(
            harness,
            "list",
            *("--profiles", "beta", "--team", "checker", "--bench", "adviser"),
            *("--phase", phase),
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout == expected
        assert result.stderr == ""


def test_the_command_line_lists_nothing_for_an_empty_roster(harness: Path) -> None:
    for phase in render_agents.PHASES:
        result = _run(
            harness,
            "list",
            *("--profiles", "alpha,beta", "--team", "", "--bench", "", "--phase", phase),
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout == ""
        assert result.stderr == ""


def test_the_command_line_without_a_roster_lists_what_c10_listed(harness: Path) -> None:
    result = _run(harness, "list", "--profiles", "alpha,beta", "--phase", "review")
    assert result.returncode == 0
    assert result.stdout == "\U0001f50d alpha-checker\n\U0001f50d beta-checker\n"
    result = _run(harness, "list", "--profiles", "alpha,beta", "--phase", "propose")
    assert result.returncode == 0
    assert result.stdout == "\U0001f9ed alpha-adviser\n"


@pytest.mark.parametrize("command", ["list", "render"])
@pytest.mark.parametrize(
    ("given", "missing"), [(("--team", "checker"), "bench"), (("--bench", ""), "team")]
)
def test_the_command_line_refuses_one_roster_option_without_the_other(
    harness: Path, command: str, given: tuple[str, str], missing: str
) -> None:
    phase = ("--phase", "review") if command == "list" else ()
    result = _run(harness, command, "--profiles", "alpha", *given, *phase)
    assert result.returncode != 0
    assert result.stdout == ""
    assert f"`{missing}` is missing" in result.stderr


def test_the_command_line_lists_a_generic_agent_with_no_profile(plugin_root: Path) -> None:
    emoji = render_agents.read_role(
        plugin_root / "orchestration" / "roles" / "security-reviewer.md"
    ).description[0]
    result = _run(
        plugin_root,
        "list",
        *("--profiles", "", "--team", "security-reviewer", "--bench", ""),
        *("--phase", "review"),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{emoji} security-reviewer\n"
    assert result.stderr == ""
