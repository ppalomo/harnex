#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Decide whether a verified change may proceed to ``/harnex:ship``.

    uv run plugin/scripts/ship_gate.py check --project <root> --change <name>

The verifier owns one stable review record per change at
``.harnex/state/verify/<change>.json``.  This script deliberately does not read the
timestamped check-facts records in that directory.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

from working_tree import tree_fingerprint


def review_record_path(project: Path, change: str) -> Path:
    """Return the verifier's stable review record path for ``change``."""
    return project / ".harnex" / "state" / "verify" / f"{change}.json"


def _valid_findings(findings: object) -> bool:
    return isinstance(findings, list) and all(
        isinstance(finding, dict)
        and isinstance(finding.get("severity"), str)
        and finding["severity"] in {"blocking", "advisory"}
        for finding in findings
    )


def record(
    project: Path,
    change: str,
    *,
    base_ref: str,
    fingerprint: str,
    findings: list[dict[str, object]],
) -> Path:
    """Atomically write the verifier's stable review record for ``change``."""
    if not _valid_findings(findings):
        raise ValueError("findings must be objects with a blocking or advisory severity")

    path = review_record_path(project, change)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{time.time_ns()}-{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(
            {
                "change": change,
                "base_ref": base_ref,
                "fingerprint": fingerprint,
                "findings": findings,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return path


def check(project: Path, change: str) -> dict[str, object]:
    """Return the unambiguous ship-gate decision for a change.

    The record's base ref is part of the verifier/ship interface.  Reusing it here
    means both sides compare exactly the tree that the verifier reviewed, even when
    callers use different base-ref conventions.
    """
    path = review_record_path(project, change)
    if not path.is_file():
        return {
            "decision": "refuse",
            "reason": "no run found",
            "findings": [],
        }

    unreadable = {
        "decision": "refuse",
        "reason": "an unreadable review record",
        "findings": [],
    }
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(stored, dict):
            return unreadable
        findings = stored["findings"]
        base_ref = stored["base_ref"]
        fingerprint = stored["fingerprint"]
        if (
            not _valid_findings(findings)
            or not isinstance(base_ref, str)
            or not base_ref
            or not isinstance(fingerprint, str)
        ):
            return unreadable
        current_fingerprint = tree_fingerprint(project, base_ref)
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, OSError, subprocess.CalledProcessError):
        return unreadable

    if current_fingerprint != fingerprint:
        return {
            "decision": "refuse",
            "reason": "stale fingerprint",
            "findings": findings,
        }

    if any(finding.get("severity") == "blocking" for finding in findings):
        return {
            "decision": "refuse",
            "reason": "a blocking finding",
            "findings": findings,
        }

    return {
        "decision": "go",
        "reason": None,
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="decide whether a verified change may ship")
    subparsers = parser.add_subparsers(dest="verb", required=True)

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--project", default=".")
    check_parser.add_argument("--change", required=True)

    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("--project", default=".")
    record_parser.add_argument("--change", required=True)
    record_parser.add_argument("--base-ref", required=True)
    record_parser.add_argument("--fingerprint", required=True)
    record_parser.add_argument(
        "--findings-json",
        required=True,
        help="a JSON findings list, or @<path> to read that JSON from a file",
    )
    args = parser.parse_args(argv)

    project = Path(args.project).resolve()
    if args.verb == "record":
        findings_json = args.findings_json
        if findings_json.startswith("@"):
            findings_json = Path(findings_json[1:]).read_text(encoding="utf-8")
        findings = json.loads(findings_json)
        if not isinstance(findings, list):
            parser.error("--findings-json must decode to a JSON list of finding objects")
        try:
            record(
                project,
                args.change,
                base_ref=args.base_ref,
                fingerprint=args.fingerprint,
                findings=findings,
            )
        except ValueError as error:
            parser.error(str(error))
        return 0

    result = check(project, args.change)
    print(json.dumps(result))
    return 0 if result["decision"] == "go" else 1


if __name__ == "__main__":
    raise SystemExit(main())
