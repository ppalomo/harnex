"""Nothing tracked in harnex may name Pablo's employer or his private infrastructure.

harnex is public and generic by design: a component knows nothing about any particular
project (docs/PLAN.md §2). That rule is cheap to state and easy to break by accident, so
this test makes it permanent. It runs in CI with the rest of the suite.

If this fails, do not just delete the line: check whether the term also reached the
history (`git log -p --all | grep -i <term>`), because the repository is public and a
blob that was ever committed stays reachable.
"""

import subprocess
from pathlib import Path

FORBIDDEN = [
    "barkibu",
    "nordic guarantee",
    "periscal",
    "aldamiz",
    "ppalomo@services",
]

# Binary payloads that would only ever match by accident.
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip"}


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [Path(p) for p in out.split("\0") if p]


def test_no_employer_terms_in_tracked_files() -> None:
    me = Path(__file__).name
    hits = []
    for path in tracked_files():
        if path.name == me or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if not path.is_file():  # submodule or deleted-but-staged entry
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        hits += [f"{path}: {term}" for term in FORBIDDEN if term in text]
    assert not hits, "employer or private infrastructure named in:\n" + "\n".join(hits)
