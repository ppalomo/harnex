"""A chosen list of sets renders one file, and always the same one.

`setup` writes the rendered file into a project and records its hash; `update` overwrites
it while that hash still matches. That only works if the bytes are a function of the
project's choices and of nothing else — not of the clock, not of the plugin's version,
not of the order the sets were typed in. Those are the properties checked here.

The snapshot pins the exact bytes of every set rendered. Regenerate it with:

    uv run plugin/scripts/render_rules.py \\
        --sets canary,code,git,language,safety,sdd --out tests/snapshots/rules-all.md

and read the diff: a rule changing is exactly the thing that should be hard to do by
accident. The smaller combinations are not snapshotted separately. They are checked
against this one by the property that makes sets safe to compose — a set renders the same
beside any other — which holds for every combination rather than for the two someone
thought to record.
"""

import subprocess
import sys
from pathlib import Path

import pytest
import render_rules
from render_rules import RuleError

REPO_ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = REPO_ROOT / "plugin" / "context" / "rules"
SCRIPT = REPO_ROOT / "plugin" / "scripts" / "render_rules.py"
SNAPSHOT = Path(__file__).resolve().parent / "snapshots" / "rules-all.md"

ALL_SETS = ["canary", "code", "git", "language", "safety", "sdd"]

PROFILE_TREE = {
    "a-set/always-applies.md": """\
---
id: always-applies
set: a-set
applies_to: always
enforced_by: none
---

# Hold for every project

Because this one is not about any particular stack.
""",
    "a-set/only-for-a-profile.md": """\
---
id: only-for-a-profile
set: a-set
applies_to: a-profile
enforced_by: none
---

# Hold only where that profile is declared

Because this one is about a stack, and says nothing to a project without it.
""",
}


def _render(sets: list[str], profiles: list[str] | None = None) -> str:
    return render_rules.render(sets, profiles, RULES_DIR)


def _sections(document: str) -> dict[str, str]:
    """The part of a rendering that belongs to each set, header excluded."""
    head, *rest = document.split("\n## ")
    return {block.split("\n", 1)[0]: block.split("\n", 1)[1] for block in rest}


@pytest.fixture
def profile_tree(tmp_path: Path) -> Path:
    for relative, text in PROFILE_TREE.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def test_it_matches_the_snapshot() -> None:
    assert _render(ALL_SETS) == SNAPSHOT.read_text(encoding="utf-8"), (
        "the rendering has moved. Read the diff, then regenerate the snapshot with the "
        "command in this module's docstring."
    )


def test_the_snapshot_holds_every_rule_once() -> None:
    sets = render_rules.load_sets(RULES_DIR)
    document = SNAPSHOT.read_text(encoding="utf-8")
    for rules in sets.values():
        for rule in rules:
            assert document.count(f"### {rule.statement}\n") == 1, (
                f"{rule.id} is not stated exactly once in the rendering"
            )


def test_the_same_choice_renders_the_same_bytes() -> None:
    assert _render(["git", "code"]) == _render(["git", "code"])


def test_the_order_asked_for_does_not_reach_the_file() -> None:
    assert _render(["git", "code", "sdd"]) == _render(["sdd", "code", "git"])


def test_a_repeated_set_renders_once() -> None:
    assert _render(["git", "code", "git"]) == _render(["git", "code"])


@pytest.mark.parametrize("name", ALL_SETS)
def test_a_set_renders_the_same_beside_any_other(name: str) -> None:
    """The property that lets setup offer sets freely."""
    assert _sections(_render([name]))[name] == _sections(_render(ALL_SETS))[name]


def test_only_the_chosen_sets_are_rendered() -> None:
    document = _render(["canary"])
    assert set(_sections(document)) == {"canary"}
    assert "Sets in this file: canary." in document


def test_the_file_ends_with_exactly_one_newline() -> None:
    document = _render(ALL_SETS)
    assert document.endswith("\n")
    assert not document.endswith("\n\n")


def test_a_profile_rule_is_absent_without_its_profile(profile_tree: Path) -> None:
    document = render_rules.render(["a-set"], [], profile_tree)
    assert "Hold for every project" in document
    assert "Hold only where that profile is declared" not in document


def test_a_profile_rule_is_present_with_its_profile(profile_tree: Path) -> None:
    document = render_rules.render(["a-set"], ["a-profile"], profile_tree)
    assert "Hold only where that profile is declared" in document


def test_an_unknown_set_is_refused() -> None:
    with pytest.raises(RuleError, match="no such set: nope"):
        _render(["git", "nope"])


def test_no_set_at_all_is_refused() -> None:
    with pytest.raises(RuleError, match="no set was chosen"):
        _render([])


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--rules-dir", str(RULES_DIR), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_screen_and_a_file_get_the_same_bytes(tmp_path: Path) -> None:
    destination = tmp_path / "rules.md"
    screen = _run("--sets", "git,code")
    written = _run("--sets", "git,code", "--out", str(destination))

    assert screen.returncode == 0 and written.returncode == 0
    assert screen.stdout == destination.read_text(encoding="utf-8")


def test_a_refusal_names_what_is_held_and_writes_nothing(tmp_path: Path) -> None:
    destination = tmp_path / "rules.md"
    result = _run("--sets", "nope", "--out", str(destination))

    assert result.returncode == 2
    assert "no such set: nope" in result.stderr
    assert "canary, code, git, language, safety, sdd" in result.stderr
    assert not destination.exists(), "a refused rendering left a file behind"
