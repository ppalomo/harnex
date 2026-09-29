"""Checks for the shell guard's conservative splitter and pattern classification."""

import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "plugin" / "control" / "guard"))

import guard  # noqa: E402  (a plugin script, reached by path)
import generate_floor  # noqa: E402  (a plugin script, reached by path)


requires_uv = pytest.mark.skipif(
    shutil.which("uv") is None, reason="uv is how the host runs this hook"
)


def _residue(
    command: str,
    *,
    cwd: Path,
    run_decide=subprocess.run,
) -> guard.Classification:
    """Reach the decision path without relying on the committed pattern coverage."""
    return guard.classify_command(
        command,
        [],
        cwd=cwd,
        branch="main",
        is_worktree=False,
        run_decide=run_decide,
    )


def test_a_compound_command_splits_into_tokenized_parts() -> None:
    assert guard.split_command("git status && git log") == [
        ("git", "status"),
        ("git", "log"),
    ]


def test_an_operator_inside_a_quoted_argument_does_not_split() -> None:
    assert guard.split_command('echo "a; b"') == [("echo", "a; b")]


@pytest.mark.parametrize(
    "command",
    [
        "echo 'unbalanced",
        "echo trailing\\",
        "echo `date`",
        "echo $(date)",
    ],
)
def test_an_unparseable_or_substituting_command_is_ambiguous(command: str) -> None:
    assert guard.split_command(command) is None


def test_an_allowlisted_read_only_command_cites_its_rule() -> None:
    segments = guard.split_command("git status --short")
    assert segments is not None

    result = guard.classify_segments(segments, guard.load_patterns())

    assert result.outcome == "allow"
    assert result.rule == "read-only-allowlist"
    assert result.pattern == "Bash(git status *)"


def test_a_deny_pattern_match_cites_its_rule() -> None:
    patterns = [
        {
            "rule": "credential-files-denied",
            "list": "deny",
            "pattern": "Bash(cat secrets/*)",
            "floor": "no",
        }
    ]
    segments = guard.split_command("cat secrets/token")
    assert segments is not None

    result = guard.classify_segments(segments, patterns)

    assert result.outcome == "deny"
    assert result.rule == "credential-files-denied"
    assert result.pattern == "Bash(cat secrets/*)"


def test_an_ask_pattern_match_cites_its_rule() -> None:
    segments = guard.split_command("git push origin main")
    assert segments is not None

    result = guard.classify_segments(segments, guard.load_patterns())

    assert result.outcome == "ask"
    assert result.rule == "pushes-ask"
    assert result.pattern == "Bash(git push *)"


def test_a_deny_classification_appends_one_guard_journal_line(tmp_path: Path) -> None:
    command = "cat secrets/token"
    result = guard.classify_command(
        command,
        [
            {
                "rule": "credential-files-denied",
                "list": "deny",
                "pattern": "Bash(cat secrets/*)",
                "floor": "no",
            }
        ],
        cwd=tmp_path,
        branch="main",
        is_worktree=False,
    )

    assert result.outcome == "deny"
    lines = guard.journal_path(tmp_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["command"] == command
    assert entry["agent_type"] is None
    assert entry["outcome"] == "deny"
    assert entry["source"] == "pattern"
    assert entry["rule"] == "credential-files-denied"
    assert entry["pattern"] == "Bash(cat secrets/*)"
    assert datetime.fromisoformat(entry["timestamp"]).tzinfo is not None


def test_an_ask_classification_appends_one_guard_journal_line(tmp_path: Path) -> None:
    command = "unrecognised-command"

    def destructive_risk(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            [],
            0,
            stdout=json.dumps(
                {
                    "resolved": True,
                    "decision": "destructive",
                    "probabilities": {
                        "destructive": 0.8,
                        "read_only": 0.1,
                        "reversible": 0.2,
                    },
                }
            ),
            stderr="",
        )

    result = guard.classify_command(
        command,
        [],
        cwd=tmp_path,
        branch="main",
        is_worktree=False,
        agent_type="builder",
        run_decide=destructive_risk,
    )

    assert result.outcome == "ask"
    lines = guard.journal_path(tmp_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["command"] == command
    assert entry["agent_type"] == "builder"
    assert entry["outcome"] == "ask"
    assert entry["source"] == "guard.risk"
    assert entry["decision"] == "destructive"
    assert entry["probabilities"] == {
        "destructive": 0.8,
        "read_only": 0.1,
        "reversible": 0.2,
    }
    assert datetime.fromisoformat(entry["timestamp"]).tzinfo is not None


def test_a_matcher_exception_asks_and_records_an_internal_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    command = "git status"

    def matcher_failure(*_args: object, **_kwargs: object) -> bool:
        raise RuntimeError("matcher failed unexpectedly")

    monkeypatch.setattr(guard, "_matches_segment", matcher_failure)

    result = guard.classify_command(
        command,
        [
            {
                "rule": "read-only-allowlist",
                "list": "allow",
                "pattern": "Bash(git status)",
                "floor": "no",
            }
        ],
        cwd=tmp_path,
        branch="main",
        is_worktree=False,
    )

    assert result.outcome == "ask"
    lines = guard.journal_path(tmp_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["command"] == command
    assert entry["outcome"] == "ask"
    assert entry["source"] == "internal_error"
    assert entry["message"] == "matcher failed unexpectedly"


def test_an_allowed_command_appends_nothing_to_the_guard_journal(tmp_path: Path) -> None:
    result = guard.classify_command(
        "git status --short",
        guard.load_patterns(),
        cwd=tmp_path,
        branch="main",
        is_worktree=False,
    )

    assert result.outcome == "allow"
    assert not guard.journal_path(tmp_path).exists()


def test_a_patternless_note_is_skipped_before_the_next_pattern_matches() -> None:
    patterns = [
        {
            "rule": "documented-guard-gap",
            "floor": "no",
            "why": "This is a note, not a command pattern.",
        },
        {
            "rule": "pushes-ask",
            "list": "ask",
            "pattern": "Bash(git push *)",
            "floor": "no",
        },
    ]
    segments = guard.split_command("git push origin main")
    assert segments is not None

    result = guard.classify_segments(segments, patterns)

    assert result.outcome == "ask"
    assert result.rule == "pushes-ask"
    assert result.pattern == "Bash(git push *)"


def test_a_role_addition_restricts_a_command_allowed_in_the_main_session() -> None:
    patterns = [
        {
            "rule": "read-only-allowlist",
            "list": "allow",
            "pattern": "Bash(make build)",
            "floor": "no",
        },
        {
            "rule": "builder-builds-ask",
            "list": "ask",
            "pattern": "Bash(make build)",
            "floor": "no",
            "agent_type": "builder",
        },
    ]
    segments = guard.split_command("make build")
    assert segments is not None

    main_session = guard.classify_segments(segments, patterns)
    builder = guard.classify_segments(segments, patterns, agent_type="builder")

    assert main_session.outcome == "allow"
    assert builder.outcome == "ask"
    assert builder.rule == "builder-builds-ask"
    assert builder.pattern == "Bash(make build)"


def test_a_role_deny_overrides_an_overlapping_default_ask() -> None:
    segments = guard.split_command("rm -rf openspec/changes")
    assert segments is not None

    main_session = guard.classify_segments(segments, guard.load_patterns())
    builder = guard.classify_segments(
        segments, guard.load_patterns(), agent_type="builder"
    )

    assert main_session.outcome == "ask"
    assert main_session.rule == "deletions-ask"
    assert builder.outcome == "deny"
    assert builder.rule == "builder-never-touches-protected-paths"


def test_floor_generation_omits_role_scoped_patterns(tmp_path: Path) -> None:
    patterns_path = tmp_path / "patterns.yaml"
    patterns_path.write_text(
        "\n".join(
            [
                "- rule: default-ask",
                "  list: ask",
                '  pattern: "Bash(default *)"',
                '  floor: "yes"',
                "- rule: builder-floor-entry",
                "  list: deny",
                '  pattern: "Bash(builder-only *)"',
                '  floor: "yes"',
                "  agent_type: builder",
                "- rule: builder-guard-only",
                "  list: deny",
                '  pattern: "Bash(builder-note *)"',
                '  floor: "no"',
                "  agent_type: builder",
                '  why: "The session-wide floor cannot express an agent role."',
                "",
            ]
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "floor.json"
    generate_floor.generate_floor(patterns_path, output_path)
    floor = json.loads(output_path.read_text(encoding="utf-8"))

    assert floor["entries"] == [
        {"rule": "default-ask", "list": "ask", "pattern": "Bash(default *)"}
    ]
    assert floor["guard_only"] == []


def test_loading_a_role_allow_entry_is_a_format_error(tmp_path: Path) -> None:
    patterns_path = tmp_path / "patterns.yaml"
    patterns_path.write_text(
        "\n".join(
            [
                "- rule: builder-cannot-loosen-defaults",
                "  list: allow",
                '  pattern: "Bash(make build)"',
                '  floor: "no"',
                "  agent_type: builder",
                "",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"patterns\.yaml: entry 1: an agent_type entry must declare `list: deny` or `list: ask`",
    ):
        guard.load_patterns(patterns_path)


def test_a_hung_decide_call_retries_once_then_asks(tmp_path: Path) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def hangs(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((argv, kwargs))
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

    result = _residue("unrecognised-command", cwd=tmp_path, run_decide=hangs)

    assert result.outcome == "ask"
    assert len(calls) == 2
    assert calls[0][0][2:] == [
        "ask",
        "--question",
        "guard.risk",
        "--decisions-dir",
        str(Path(guard.__file__).resolve().parent),
        "--state",
        "-",
    ]
    assert calls[0][1]["timeout"] == 3
    assert json.loads(calls[0][1]["input"]) == {
        "command": "unrecognised-command",
        "cwd": str(tmp_path),
        "branch": "main",
        "is_worktree": False,
    }


def test_a_failed_decide_call_retries_and_uses_the_second_answer(tmp_path: Path) -> None:
    calls = 0

    def five_xx_then_success(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return subprocess.CompletedProcess([], 1, stdout="", stderr="HTTP 503")
        return subprocess.CompletedProcess(
            [],
            0,
            stdout=json.dumps({"resolved": True, "decision": "destructive"}),
            stderr="",
        )

    result = _residue(
        "unrecognised-command", cwd=tmp_path, run_decide=five_xx_then_success
    )

    assert calls == 2
    assert result.outcome == "ask"


def test_a_genuinely_mock_backend_is_unresolved_and_asks(tmp_path: Path) -> None:
    result = _residue("unrecognised-command", cwd=tmp_path)

    assert result.outcome == "ask"
    journal = json.loads((tmp_path / ".harnex" / "state" / "journal.jsonl").read_text())
    assert journal["backend"] == "mock"
    assert journal["resolution"] is None


def test_a_missing_api_key_from_decide_asks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".harnex.yml").write_text(
        """project_name: scratch
profiles:
sets:
  - git
features:
canary: \"\"
decision_model: jev
check_command: make check
""",
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    result = _residue("unrecognised-command", cwd=tmp_path)

    assert result.outcome == "ask"
    journal = json.loads((tmp_path / ".harnex" / "state" / "journal.jsonl").read_text())
    assert journal["backend"] == "jev"
    assert journal["resolution"] is None


# --- the hook, run as the host runs it -------------------------------------------------


@pytest.fixture
def bash_payload(project: Path):
    """Recorded Claude Code PreToolUse input, varied only at the decision point."""

    def make(command: str, *, agent_type: str | None = None) -> dict[str, object]:
        payload: dict[str, object] = {
            "session_id": "abc123",
            "cwd": str(project),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": command,
                "description": "a recorded Bash invocation",
                "timeout": 120000,
                "run_in_background": False,
            },
            "tool_use_id": "toolu_recorded",
        }
        if agent_type is not None:
            payload["agent_id"] = "subagent-recorded"
            payload["agent_type"] = agent_type
        return payload

    return make


def _pretool_hook(plugin_root: Path) -> tuple[list[str], int]:
    """Read the exact Bash hook command from the installed manifest."""
    manifest = json.loads((plugin_root / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    entry = manifest["hooks"]["PreToolUse"][0]
    assert entry["matcher"] == "Bash"
    hook = entry["hooks"][0]
    assert hook["type"] == "command"
    command = hook["command"].replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_root))
    return shlex.split(command), hook["timeout"]


def _run_guard_hook(
    plugin_root: Path,
    project: Path,
    payload: dict[str, object],
    *,
    sitecustomize: Path | None = None,
    project_dir: bool = True,
) -> subprocess.CompletedProcess[str]:
    argv, timeout = _pretool_hook(plugin_root)
    env = dict(os.environ)
    if project_dir:
        env["CLAUDE_PROJECT_DIR"] = str(project)
    else:
        env.pop("CLAUDE_PROJECT_DIR", None)
    if sitecustomize is not None:
        env["PYTHONPATH"] = str(sitecustomize) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        argv,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout + 10,
    )


def _hook_decision(finished: subprocess.CompletedProcess[str], expected: str) -> None:
    assert finished.returncode == 0, finished.stderr
    output = json.loads(finished.stdout)
    specific = output["hookSpecificOutput"]
    assert specific["hookEventName"] == "PreToolUse"
    assert specific["permissionDecision"] == expected
    if expected == "allow":
        assert specific == {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    else:
        assert isinstance(specific["permissionDecisionReason"], str)
        assert specific["permissionDecisionReason"]


def _fake_decide_sitecustomize(directory: Path, outcome: dict[str, object]) -> Path:
    """Make only the child hook's real ``decide.py`` subprocess return ``outcome``."""
    directory.mkdir()
    encoded = json.dumps(outcome)
    (directory / "sitecustomize.py").write_text(
        f'''\
import subprocess

_run = subprocess.run
_outcome = {encoded!r}

def run(argv, *args, **kwargs):
    if len(argv) > 1 and str(argv[1]).endswith("/decide.py"):
        return subprocess.CompletedProcess(argv, 0, stdout=_outcome, stderr="")
    return _run(argv, *args, **kwargs)

subprocess.run = run
''',
        encoding="utf-8",
    )
    return directory


def _malformed_patterns_sitecustomize(directory: Path) -> Path:
    """Make the script's own pattern reader fail without modifying the real fixture."""
    directory.mkdir()
    (directory / "sitecustomize.py").write_text(
        '''\
import importlib.abc
import importlib.util
import sys

class Loader(importlib.abc.Loader):
    def create_module(self, spec):
        return None

    def exec_module(self, module):
        def load_patterns(path):
            raise ValueError(f"{path}: malformed patterns fixture")
        module.load_patterns = load_patterns

class Finder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "generate_floor":
            return importlib.util.spec_from_loader(fullname, Loader())
        return None

sys.meta_path.insert(0, Finder())
''',
        encoding="utf-8",
    )
    return directory


def _copy_guard_without_generate_floor(plugin_root: Path, directory: Path) -> Path:
    """Copy the hook script without the sibling module it imports before ``main()``."""
    copied_guard = directory / "plugin" / "control" / "guard"
    copied_guard.mkdir(parents=True)
    shutil.copy2(plugin_root / "control" / "guard" / "guard.py", copied_guard)
    return copied_guard / "guard.py"


def _copy_guard_with_hanging_decide(plugin_root: Path, directory: Path) -> Path:
    """Build a temporary plugin layout whose real ``decide.py`` never returns."""
    copied_plugin = directory / "plugin"
    copied_guard = copied_plugin / "control" / "guard"
    copied_guard.mkdir(parents=True)
    for name in ("guard.py", "generate_floor.py", "patterns.yaml", "guard-risk.yaml"):
        shutil.copy2(plugin_root / "control" / "guard" / name, copied_guard / name)

    scripts = copied_plugin / "scripts"
    scripts.mkdir()
    (scripts / "decide.py").write_text(
        "import time\ntime.sleep(60)\n", encoding="utf-8"
    )
    return copied_guard / "guard.py"


def _assert_no_guard_decision(finished: subprocess.CompletedProcess[str]) -> None:
    """Assert only the observable precondition for the host fallback guarantee."""
    assert finished.returncode != 0
    assert finished.stdout == ""
    with pytest.raises(json.JSONDecodeError):
        json.loads(finished.stdout)


@requires_uv
def test_pretool_hook_allows_a_read_only_command_from_payload_cwd(
    plugin_root: Path, project: Path, bash_payload
) -> None:
    finished = _run_guard_hook(
        plugin_root,
        project,
        bash_payload("git status --short"),
        project_dir=False,
    )
    _hook_decision(finished, "allow")


@requires_uv
def test_pretool_hook_asks_for_an_ask_pattern(
    plugin_root: Path, project: Path, bash_payload
) -> None:
    finished = _run_guard_hook(
        plugin_root, project, bash_payload("git push origin main", agent_type="Explore")
    )
    _hook_decision(finished, "ask")


@requires_uv
@pytest.mark.parametrize(
    ("risk_outcome", "expected"),
    [
        ({"resolved": True, "decision": "read_only"}, "allow"),
        ({"resolved": True, "decision": "destructive"}, "ask"),
    ],
    ids=["guard-risk-read-only", "guard-risk-destructive"],
)
def test_pretool_hook_uses_guard_risk_outcomes(
    tmp_path: Path,
    plugin_root: Path,
    project: Path,
    bash_payload,
    risk_outcome: dict[str, object],
    expected: str,
) -> None:
    sitecustomize = _fake_decide_sitecustomize(tmp_path / "fake-decide", risk_outcome)
    finished = _run_guard_hook(
        plugin_root,
        project,
        bash_payload("unrecognised-command"),
        sitecustomize=sitecustomize,
    )
    _hook_decision(finished, expected)


@requires_uv
def test_pretool_hook_asks_when_guard_risk_backend_is_unresolved(
    plugin_root: Path, project: Path, bash_payload
) -> None:
    # No .harnex.yml makes decide.py use its real mock backend, which is unresolved.
    finished = _run_guard_hook(
        plugin_root, project, bash_payload("unrecognised-command")
    )
    _hook_decision(finished, "ask")
    reason = json.loads(finished.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "mock_backend" in reason


@requires_uv
def test_pretool_hook_asks_on_a_malformed_patterns_fixture(
    tmp_path: Path, plugin_root: Path, project: Path, bash_payload
) -> None:
    sitecustomize = _malformed_patterns_sitecustomize(tmp_path / "malformed-patterns")
    finished = _run_guard_hook(
        plugin_root,
        project,
        bash_payload("git status"),
        sitecustomize=sitecustomize,
    )
    _hook_decision(finished, "ask")
    reason = json.loads(finished.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "malformed patterns fixture" in reason


@requires_uv
def test_pretool_hook_with_a_missing_interpreter_cannot_produce_a_guard_decision(
    tmp_path: Path, plugin_root: Path, project: Path, bash_payload
) -> None:
    argv, _ = _pretool_hook(plugin_root)
    argv[0] = str(tmp_path / "missing-uv")

    with pytest.raises(FileNotFoundError):
        subprocess.run(
            argv,
            input=json.dumps(bash_payload("git status --short")),
            capture_output=True,
            text=True,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)},
        )


@requires_uv
def test_pretool_hook_crashing_before_main_emits_no_guard_decision(
    tmp_path: Path, plugin_root: Path, project: Path, bash_payload
) -> None:
    script = _copy_guard_without_generate_floor(plugin_root, tmp_path / "missing-import")
    finished = subprocess.run(
        ["uv", "run", "--quiet", str(script)],
        input=json.dumps(bash_payload("git status --short")),
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)},
    )

    _assert_no_guard_decision(finished)
    assert "generate_floor" in finished.stderr


@requires_uv
def test_pretool_hook_bounds_a_real_hanging_decide_process(
    tmp_path: Path, plugin_root: Path, project: Path, bash_payload
) -> None:
    """The inner timeout prevents a real child hang from reaching the host timeout."""
    script = _copy_guard_with_hanging_decide(plugin_root, tmp_path / "hanging-decide")
    started = time.monotonic()
    finished = subprocess.run(
        ["uv", "run", "--quiet", str(script)],
        input=json.dumps(bash_payload("unrecognised-command")),
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)},
        timeout=10,
    )

    assert time.monotonic() - started < 10
    _hook_decision(finished, "ask")
    reason = json.loads(finished.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "backend failure" in reason


# There is deliberately no malformed-stdout fixture.  ``main()`` catches every runtime
# exception, makes one ``json.dumps`` call, and exits successfully; inducing malformed
# stdout would require replacing that CLI or the standard library, not exercising a real
# hook failure.  Malformed bytes introduced outside this process remain a host concern,
# for which the README guarantees the normal permission flow takes over.


def test_diagram_05_has_no_default_bash_deny_fixture_today() -> None:
    """Diagram 05's main-session deny row remains empty in the default lists."""
    assert not [
        record
        for record in guard.load_patterns()
        if "agent_type" not in record
        and record.get("list") == "deny"
        and record.get("pattern", "").startswith("Bash(")
    ]
