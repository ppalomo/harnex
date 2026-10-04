#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Detect the plugin's own identity and the version a bump could produce.

The project's root marketplace manifest and its single plugin's own manifest are
expected to agree on a name and a version; ``detect`` reads both and refuses, with a
short reason, whenever there is no single entry to read, its source does not resolve
to a manifest, or the two manifests disagree.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path


def _candidates(version: str) -> dict[str, str]:
    """Return the three ``X.Y.Z`` candidates a bump of ``version`` could produce."""
    major, minor, patch = (int(part) for part in version.split("."))
    return {
        "patch": f"{major}.{minor}.{patch + 1}",
        "minor": f"{major}.{minor + 1}.0",
        "major": f"{major + 1}.0.0",
    }


def detect(project: Path) -> dict[str, object]:
    """Return the plugin's own identity and version candidates, or why not.

    Reads ``project``'s root ``.claude-plugin/marketplace.json``, resolves its single
    ``plugins[]`` entry's ``source``, and reads that plugin's own
    ``.claude-plugin/plugin.json``. Returns ``{"found": True, ...}`` only when exactly
    one entry exists and its name and version agree with the plugin manifest's own;
    returns ``{"found": False, "reason": ...}`` for every other case.
    """
    marketplace_path = project / ".claude-plugin" / "marketplace.json"
    if not marketplace_path.is_file():
        return {"found": False, "reason": "no marketplace.json found"}

    try:
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {"found": False, "reason": "an unreadable marketplace.json"}

    plugins = marketplace.get("plugins") if isinstance(marketplace, dict) else None
    if not isinstance(plugins, list) or len(plugins) != 1:
        count = len(plugins) if isinstance(plugins, list) else 0
        return {
            "found": False,
            "reason": f"expected exactly one plugin entry, found {count}",
        }

    entry = plugins[0]
    if not isinstance(entry, dict):
        return {"found": False, "reason": "an unreadable plugin entry"}

    source = entry.get("source")
    if not isinstance(source, str) or not source:
        return {"found": False, "reason": "an unresolved plugin source"}

    manifest_path = project / source / ".claude-plugin" / "plugin.json"
    if not manifest_path.is_file():
        return {"found": False, "reason": "an unresolved plugin source"}

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {"found": False, "reason": "an unreadable plugin.json"}

    if not isinstance(manifest, dict):
        return {"found": False, "reason": "an unreadable plugin.json"}

    entry_name, entry_version = entry.get("name"), entry.get("version")
    manifest_name, manifest_version = manifest.get("name"), manifest.get("version")

    if entry_name != manifest_name or entry_version != manifest_version:
        return {
            "found": False,
            "reason": "the marketplace entry and the plugin manifest disagree",
        }

    if not isinstance(manifest_version, str):
        return {"found": False, "reason": "an unreadable plugin.json"}

    try:
        candidates = _candidates(manifest_version)
    except ValueError:
        return {"found": False, "reason": "an unparsable version"}

    return {
        "found": True,
        "marketplace_path": marketplace_path,
        "manifest_path": manifest_path,
        "name": manifest_name,
        "current_version": manifest_version,
        "candidates": candidates,
    }


def _write_json_atomic(path: Path, data: object) -> None:
    """Write ``data`` as indented JSON to ``path``, atomically.

    Uses the same temporary-file-then-``os.replace`` pattern as
    ``ship_gate.record``, so a reader never observes a half-written file.
    """
    temporary = path.with_name(f".{path.name}.{time.time_ns()}-{os.getpid()}.tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def bump(project: Path, level: str) -> str:
    """Bump the plugin's own version by ``level`` and return the new version.

    Re-runs ``detect`` and refuses, raising ``ValueError``, if ``project`` no longer
    has the same single, agreeing manifest ``detect`` requires. Otherwise writes the
    chosen candidate version into both the plugin manifest's own ``version`` and the
    marketplace entry's ``version``, each via a parsed-JSON round trip that preserves
    the file's existing key order and touches no other key — in particular, the
    marketplace's own top-level ``metadata.version`` is left untouched.
    """
    if level not in {"patch", "minor", "major"}:
        raise ValueError(f"unknown bump level: {level!r}")

    result = detect(project)
    if not result["found"]:
        raise ValueError(f"cannot bump: {result['reason']}")

    new_version = result["candidates"][level]
    manifest_path = result["manifest_path"]
    marketplace_path = result["marketplace_path"]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = new_version
    _write_json_atomic(manifest_path, manifest)

    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    marketplace["plugins"][0]["version"] = new_version
    _write_json_atomic(marketplace_path, marketplace)

    return new_version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="detect the plugin's own version, or bump it"
    )
    subparsers = parser.add_subparsers(dest="verb", required=True)

    detect_parser = subparsers.add_parser("detect")
    detect_parser.add_argument("--project", default=".")

    bump_parser = subparsers.add_parser("bump")
    bump_parser.add_argument("--project", default=".")
    bump_parser.add_argument(
        "--level", required=True, choices=["patch", "minor", "major"]
    )

    args = parser.parse_args(argv)
    project = Path(args.project).resolve()

    if args.verb == "detect":
        print(json.dumps(detect(project), default=str))
        return 0

    before = detect(project)
    try:
        new_version = bump(project, args.level)
    except ValueError as error:
        print(json.dumps({"error": str(error)}))
        return 1

    print(
        json.dumps(
            {
                "name": before["name"],
                "from_version": before["current_version"],
                "to_version": new_version,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
