## Why

`README.md` tells a stranger how to install harnex into *another* project and lists the
five workflow commands, but says nothing about how to get set up to work **inside this
repository** — clone it, enable `.githooks`, run `uv run --with pytest pytest` — or about
the phases a change moves through while developing harnex itself (the OpenSpec-driven
cycle: `explore` → `propose` → `apply` → `verify` → `ship`/archive, named in `AGENTS.md`
and detailed in `docs/PLAN.md`). Today a contributor has to read `AGENTS.md` and
`docs/PLAN.md` end to end to piece that together, and the README has no diagram of its
own — it only links out to the excalidraw files under `docs/diagrams/`, which do not
render inline on GitHub.

## What Changes

- Expand the "🛠 Developing harnex" section of `README.md` into a short, self-contained
  guide for someone about to work *on* this repository: cloning it, enabling the commit
  hook (`git config core.hooksPath .githooks`), and running the check command.
- Add the phases a change follows while being developed in this repo (proposal → specs →
  design → tasks, then `apply` → `verify` → `ship`/archive), summarised from `AGENTS.md`
  and `docs/PLAN.md` §3–§11, without restating their full detail.
- Add two diagrams rendered inline in the README with GitHub-native Mermaid (no new
  tooling, no change to `docs/diagrams/build.py` or the existing `.excalidraw` files):
  one for the in-repo setup flow, one for the phases a change goes through.
- Keep the existing "📦 Installing it" section (installing the harnex *plugin* into an
  external project) as is; only its heading/intro is clarified so it is not confused with
  the new in-repo contributor section.
- Documentation only: no file under `plugin/`, `openspec/specs/`, or any hook/script
  changes.

## Capabilities

This is a documentation-only change: no spec-level behaviour changes. `skip_specs: true`
is set in this change's `.openspec.yaml`.

### New Capabilities

None.

### Modified Capabilities

None.

## Non-Goals

- Regenerating or editing the `.excalidraw` diagrams under `docs/diagrams/`, or changing
  `docs/diagrams/build.py`.
- Rewriting `docs/PLAN.md` or `AGENTS.md` — the README summarises them, it does not
  replace them.
- Changing the "📦 Installing it" instructions for installing the harnex plugin into an
  external project, or any plugin/command/hook behaviour.
- Adding a diagramming dependency beyond GitHub's native Mermaid rendering.

## Pillar and phase

No `plugin/` pillar is touched; this is documentation only. It belongs to `C6`'s own exit
criterion, not a new phase: `C6` delivered "the README rewritten for a stranger ...
documented alongside the five commands", but that rewrite only covers installing the
*plugin* into a project, not setting up and working in *this* repository. This change
closes that gap in the same document C6 already owns.

## Impact

- `README.md` only. No code, spec, hook, or script under `plugin/` changes.
- `openspec/changes/readme-dev-workflow/.openspec.yaml` carries `skip_specs: true`.
