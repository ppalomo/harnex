#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Warn when the main session's last answer does not end with the canary word.

Pillar 5's Stop hook. Reads the payload the host passes at the end of a turn, and warns
the person — never the model — when the project chose the `canary` set and the answer
does not end with the word `.harnex.yml` records. Inert in any project without that file
or without that set. Standard library only; the file's one reader is setup's own
`parse_choices`, imported by path, so `.harnex.yml` has one schema and one error message
per fault.

    uv run plugin/feedback/canary/canary.py < payload.json

Never blocks: the script always exits 0, and the only thing it ever prints is at most
one `systemMessage`.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

import setup as setup_script  # noqa: E402  (a plugin script, reached by path)

CANARY_SET = "canary"
CHOICES_NAME = setup_script.CHOICES  # ".harnex.yml"

# What "ends with the word" means: strip trailing whitespace, then any trailing run of
# the marks a model wraps a word in (bold, italics, code) with whitespace between them,
# then compare the end of what is left with the word exactly, case included.
_TRAILING_DECORATION = re.compile(r"[\s*_`]+$")


def _ends_with_word(answer: str, word: str) -> bool:
    return _TRAILING_DECORATION.sub("", answer).endswith(word)


def _resolve_project_root(payload: dict) -> Path:
    """The host sets `CLAUDE_PROJECT_DIR` for hooks; otherwise fall back to the
    payload's own `cwd`. Either way, this project's root only — no walking up."""
    root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or "."
    return Path(root)


def _check(raw: str) -> str | None:
    """Return the one message to print, or ``None`` to stay silent.

    The failures this function recognises become a "not checked" message with the
    reason; anything else propagates to `main`, which reports it the same way rather
    than let the script crash silently or lie about what it verified.
    """
    payload = json.loads(raw)
    project_root = _resolve_project_root(payload)
    choices_path = project_root / CHOICES_NAME

    if not choices_path.is_file():
        return None  # inert: this project never ran setup

    try:
        choices = setup_script.parse_choices(
            choices_path.read_text(encoding="utf-8"), str(choices_path)
        )
    except (OSError, setup_script.SetupError) as error:
        return f"the canary was not checked: {choices_path} could not be read ({error})"

    if CANARY_SET not in choices.get("sets", []):
        return None  # inert: this project did not choose the set

    word = str(choices.get("canary", ""))
    if not word.strip():
        return (
            f"the canary was not checked: the `{CANARY_SET}` set is chosen in "
            f"{choices_path}, but no word is recorded"
        )

    answer = payload.get("last_assistant_message")
    if not answer:
        return None  # nothing to judge: no text, or the turn ended on a tool call

    if _ends_with_word(answer, word):
        return None

    return (
        f"The canary word `{word}` is missing from the end of this answer. This "
        "instruction was not followed, which is a signal the project's rules may no "
        "longer be in effect. Compacting or starting a new session is the usual remedy."
    )


def main() -> int:
    try:
        message = _check(sys.stdin.read())
    except json.JSONDecodeError as error:
        message = (
            f"the canary was not checked: the hook's input is not readable JSON ({error})"
        )
    except Exception as error:  # report, never crash silently and never lie
        message = f"the canary was not checked: an unexpected error occurred ({error})"

    if message:
        print(json.dumps({"systemMessage": message}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
