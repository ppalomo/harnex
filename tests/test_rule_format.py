"""Every rule is stated once, in the format a check can read.

The constraint this holds is the one the plan calls a bug when it breaks: a rule is
stated exactly once, and if it is also enforced, the enforcement lives in another pillar
and the rule names it. The format exists to make that checkable, so the format itself is
checked here — on the real tree, and on trees seeded with each fault it must catch.

The seeded faults are written to temporary directories rather than into the real tree:
a rule file is prose someone will be editing, and a check that mutates it in place can
lose a draft.
"""

from pathlib import Path

import pytest
import render_rules
from render_rules import ENFORCEMENT_KINDS, RuleError

EXPECTED_SETS = {"git", "code", "sdd", "safety", "canary", "language"}

ENFORCER_LINE = "**Enforced by:**"

REPO_ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = REPO_ROOT / "plugin" / "context" / "rules"
RULE_FILES = sorted(RULES_DIR.glob("*/*.md"))

GOOD_RULE = """\
---
id: a-rule
set: a-set
applies_to: always
enforced_by: none
---

# Do the thing that this rule is about

Because otherwise the other thing happens, and nobody wants that.
"""


def _seed(tmp_path: Path, text: str, name: str = "a-rule.md") -> Path:
    """Write one rule into a throwaway set and return its directory."""
    directory = tmp_path / "a-set"
    directory.mkdir(exist_ok=True)
    (directory / name).write_text(text, encoding="utf-8")
    return directory


def _rule(path: Path) -> render_rules.Rule:
    return render_rules.parse_rule(path, path.parent.name)


def test_there_is_at_least_one_rule() -> None:
    assert RULE_FILES, f"no rule files under {RULES_DIR}"


def test_the_expected_sets_are_present() -> None:
    held = set(render_rules.available_sets(RULES_DIR))
    assert held == EXPECTED_SETS, f"sets held: {sorted(held)}"


def test_every_set_holds_at_least_one_rule() -> None:
    sets = render_rules.load_sets(RULES_DIR)
    empty = sorted(name for name, rules in sets.items() if not rules)
    assert not empty, f"sets with no rule in them: {empty}"


def test_every_rule_belongs_to_exactly_one_set() -> None:
    sets = render_rules.load_sets(RULES_DIR)
    ids = [rule.id for rules in sets.values() for rule in rules]
    assert len(ids) == len(set(ids)), "a rule is stated once"
    assert len(ids) == len(RULE_FILES)


@pytest.mark.parametrize("path", RULE_FILES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_the_rule_is_in_the_format(path: Path) -> None:
    """Four fields, the right values, and a body that opens with the rule itself."""
    rule = _rule(path)
    assert rule.id == path.stem
    assert rule.set == path.parent.name
    assert rule.enforced_by in ENFORCEMENT_KINDS
    assert rule.statement, "the rule states nothing"
    assert rule.reason, "the rule gives no reason"


@pytest.mark.parametrize("path", RULE_FILES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_applies_to_is_always_or_a_profile_that_exists(path: Path, plugin_root: Path) -> None:
    """The field is a real cross-pillar link, not a label.

    No profile exists before C3, so today every rule is `always` and this passes without
    reaching the filesystem. It becomes a live check the moment the first profile lands.
    """
    rule = _rule(path)
    if rule.applies_to == render_rules.ALWAYS:
        return
    profile = plugin_root / "tools" / "profiles" / rule.applies_to
    assert profile.is_dir(), (
        f"{path}: applies_to `{rule.applies_to}`, which is no profile the harness holds"
    )


@pytest.mark.parametrize("path", RULE_FILES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_an_enforced_rule_names_its_enforcer(path: Path) -> None:
    """From the rule you can find the code. C1d walks the other way, to the hook."""
    rule = _rule(path)
    names_one = ENFORCER_LINE in rule.reason
    if rule.enforced_by == "none":
        assert not names_one, (
            f"{path}: names an enforcer but declares `enforced_by: none`"
        )
    else:
        assert names_one, (
            f"{path}: declares `enforced_by: {rule.enforced_by}` but its body names no "
            f"enforcer. Add a `{ENFORCER_LINE}` line saying which component enforces it."
        )


@pytest.mark.parametrize(
    ("fault", "text", "expected"),
    [
        ("no frontmatter", GOOD_RULE.split("---\n")[-1], "frontmatter block"),
        ("unclosed frontmatter", GOOD_RULE.replace("enforced_by: none\n---\n", "enforced_by: none\n"), "never closed"),
        ("a missing field", GOOD_RULE.replace("applies_to: always\n", ""), "declares no applies_to"),
        ("an unknown field", GOOD_RULE.replace("id: a-rule", "id: a-rule\nseverity: high"), "does not hold"),
        ("a nested value", GOOD_RULE.replace("applies_to: always", "applies_to:\n  - always"), "not `key: value`"),
        ("a list value", GOOD_RULE.replace("applies_to: always", "applies_to: [always]"), "not a plain string"),
        ("a duplicated field", GOOD_RULE.replace("id: a-rule", "id: a-rule\nid: a-rule"), "declared twice"),
        ("an id that is not the file name", GOOD_RULE.replace("id: a-rule", "id: another-rule"), "but is named"),
        ("a set that is not the directory", GOOD_RULE.replace("set: a-set", "set: elsewhere"), "but is stored in"),
        ("an unknown enforcement", GOOD_RULE.replace("enforced_by: none", "enforced_by: vibes"), "is not one of"),
        ("no rule stated", GOOD_RULE.replace("# Do the thing that this rule is about", "Do the thing"), "must open with"),
        ("a heading that is not the rule", GOOD_RULE.replace("# Do the thing", "## Do the thing"), "must open with"),
        ("a second heading", GOOD_RULE + "\n## And another thing\n\nmore\n", "a second heading"),
        ("no reason", GOOD_RULE.split("Because")[0], "no reason"),
    ],
)
def test_the_format_check_catches(tmp_path: Path, fault: str, text: str, expected: str) -> None:
    """The check fails on trees it should reject, not only passes on the real one."""
    directory = _seed(tmp_path, text)
    with pytest.raises(RuleError, match=expected):
        _rule(directory / "a-rule.md")


def test_the_same_rule_in_two_sets_is_caught(tmp_path: Path) -> None:
    _seed(tmp_path, GOOD_RULE)
    other = tmp_path / "b-set"
    other.mkdir()
    (other / "a-rule.md").write_text(GOOD_RULE.replace("set: a-set", "set: b-set"), encoding="utf-8")

    with pytest.raises(RuleError, match="A rule is stated once"):
        render_rules.load_sets(tmp_path)


def test_a_good_rule_passes(tmp_path: Path) -> None:
    """The faults above are faults, and what they were derived from is not."""
    directory = _seed(tmp_path, GOOD_RULE)
    rule = _rule(directory / "a-rule.md")
    assert rule.statement == "Do the thing that this rule is about"
