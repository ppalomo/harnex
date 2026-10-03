## 1. Draft the in-repo contributor content

- [x] 1.1 Draft the "set up this repo" steps (clone, `git config core.hooksPath
  .githooks`, `uv run --with pytest pytest`) and verify each step matches what
  `AGENTS.md`'s "Git" and "Tests" sections already say — no new command invented.
- [x] 1.2 Draft the phases summary for working on a change in this repo (`explore` →
  `propose` → `apply` → `verify` → `ship`, with the OpenSpec artifacts — proposal, specs,
  design, tasks — a `propose` produces) sourced from `AGENTS.md`'s "Method" section and
  `docs/PLAN.md` §3 and §11, and verify it introduces no claim absent from those two
  files.

## 2. Add inline diagrams

- [x] 2.1 Add a GitHub-flavoured Mermaid diagram for the in-repo setup flow (clone →
  enable the commit hook → run the check command) and verify it renders correctly in a
  local Markdown preview (VS Code's or GitHub's own Mermaid preview) with no syntax
  error.
- [x] 2.2 Add a second Mermaid diagram for the phases a change moves through in this repo
  (the artifacts `propose` produces, then `apply` → `verify` → `ship`/archive) and verify
  it renders correctly the same way.

## 3. Integrate into the README

- [x] 3.1 Rewrite the "🛠 Developing harnex" section of `README.md` using 1.1, 1.2, 2.1
  and 2.2, keeping the existing `uv run --with pytest pytest` and
  `python3 docs/diagrams/build.py` commands and the link to `AGENTS.md`; verify by
  reading the section top to bottom as a stranger who has never seen this repo would.
- [x] 3.2 Clarify the "📦 Installing it" section's heading or intro line so it reads
  unambiguously as installing the harnex *plugin* into another project, distinct from
  the new in-repo section added in 3.1; verify the two sections no longer share wording
  that could be read as the same instructions.

## 4. Check

- [x] 4.1 Run `uv run --with pytest pytest` and confirm it still passes with only
  `README.md` changed.

## 5. Plan sync

- [x] 5.1 Update `docs/PLAN.md` so its description of the README (`C6`'s "Delivers"
  bullet) also notes that the README now documents the in-repo setup and phase workflow
  for contributors, not only installing the plugin into a project; verify by re-reading
  that bullet against the final `README.md`.
