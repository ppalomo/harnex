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


# --- the real roles -----------------------------------------------------------------


def test_the_real_roles_render_against_a_fixture_profile(
    plugin_root: Path, tmp_path: Path
) -> None:
    """The plugin's own roles, with a team built here so no shipped profile is needed."""
    profiles = tmp_path / "profiles"
    team = profiles / "omega"
    team.mkdir(parents=True)
    (team / "profile.md").write_text("# omega\n", encoding="utf-8")
    for specialist in ("reviewer", "security-reviewer", "api-designer"):
        (team / f"{specialist}.md").write_text(f"On omega, as {specialist}.\n")

    agents = render_agents.render(["omega"], plugin_root, profiles)

    assert list(agents) == [
        ".claude/agents/omega-api-designer.md",
        ".claude/agents/omega-reviewer.md",
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
    for specialist in ("reviewer", "security-reviewer", "api-designer"):
        (team / f"{specialist}.md").write_text(f"On omega, as {specialist}.\n")

    def emoji(role: str) -> str:
        path = plugin_root / "orchestration" / "roles" / f"{role}.md"
        return render_agents.read_role(path).description[0]

    review = render_agents.agents_for(["omega"], "review", plugin_root, profiles)
    assert [(agent.name, agent.emoji) for agent in review] == [
        ("omega-reviewer", emoji("reviewer")),
        ("omega-security-reviewer", emoji("security-reviewer")),
    ]
    assert [agent.emoji for agent in review] == ["\U0001f50d", "\U0001f510"]

    propose = render_agents.agents_for(["omega"], "propose", plugin_root, profiles)
    assert [(agent.name, agent.emoji) for agent in propose] == [
        ("omega-api-designer", emoji("api-designer"))
    ]
    assert propose[0].emoji == "\U0001f50c"

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
