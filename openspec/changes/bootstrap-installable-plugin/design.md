## Context

The repository today holds a plan, seven diagrams and an OpenSpec setup. Nothing is
installable. See `proposal.md` — Why for the motivation; the behaviour this design has to
satisfy is in `specs/plugin-delivery/spec.md`.

Two facts were established by hand against Claude Code `2.1.267` before writing this,
because they decide the shape of the manifests:

- A plugin with **no components at all** — no commands, skills, agents or hooks — passes
  `claude plugin validate <dir> --strict`. Emptiness is not a warning. This is what makes
  C1a viable as a change of its own.
- `--strict` treats warnings as errors, and two warnings appear on a bare manifest: a
  missing `author` in `plugin.json`, and a missing marketplace description. With
  `author` and `metadata.description` present, both manifests pass strict cleanly.

The second fact is the whole reason this design fixes a field list instead of writing the
smallest manifest that parses.

## Goals / Non-Goals

**Goals:**

- One installed unit that contains the harness and nothing else — not the plan, not the
  diagrams, not this repository's own OpenSpec data.
- Manifests that pass strict validation on the verified Claude Code version, with the
  fewest fields that do so, so a schema change costs one field.
- A layout check that fails loudly the first time a component is put in the wrong place,
  while the directories are still empty and moving it is free.
- A private-name check that can be run by anyone without publishing the private names.

**Non-Goals:**

- Any contributed behaviour. The plugin installs and adds nothing to a session; the
  spec makes that a requirement rather than an accident.
- CI. The three checks run by hand here and are wired into CI in `C6`.
- Tags and release policy; also `C6`.

## Decisions

**The catalogue sits at the repository root; the plugin sits in `plugin/`.**
`.claude-plugin/marketplace.json` lists one plugin with `source: "./plugin"`. The
alternative — the plugin at the repository root — would install `docs/`, `openspec/` and
the diagrams onto every machine, and would leave no place to put the repository's own
tests. The cost is one level of nesting and the `source` field.

**The manifests carry the minimum field set that passes strict, and no more.**
`plugin.json`: `name`, `version`, `description`, `author`; plus `homepage`, `repository`,
`license` and `keywords`, which are free and make the catalogue entry readable.
`marketplace.json`: `name`, `owner`, `metadata.description`, and the single plugin entry.
`author` and `metadata.description` are not decoration — without them strict fails, as
measured above. Decision 9 of the plan (minimum frontmatter) is the same instinct applied
to manifests: every field present is a field to migrate later.

**Validation is two commands, not one.** The plugin manifest and the marketplace manifest
validate separately, and only the pair covers the path a stranger walks: add the
marketplace, then install the plugin. The task list runs both.

**Each pillar directory is created with a `README.md`, not a `.gitkeep`.** Git cannot
track an empty directory, so something must be committed; the spec independently requires
each pillar to state what it holds. One file does both jobs. Each README says what
belongs in that pillar, what does not, and which later change fills it — so the first
person to add a component reads the boundary before crossing it.

**The layout check is a test, not a convention.** A test walks `plugin/` and fails on any
directory that is neither a pillar (`context`, `tools`, `orchestration`, `control`,
`feedback`) nor a directory Claude Code itself reads (`commands`, `skills`, `agents`,
`hooks`, `scripts`, `.claude-plugin`), and on any pillar missing its README. The
alternative — writing the rule in `AGENTS.md` and trusting it — is exactly the failure
mode the plan calls a bug: a rule with no enforcement.

**The private-name denylist is split, because the check cannot contain what it forbids.**
A committed denylist of private names would publish the private names. So the committed
half holds only shapes that are private by construction — credential-looking tokens,
`.env` contents, absolute paths under a home directory, private host suffixes — and the
personal half lives in a file the repository never tracks, found through an environment
variable and ignored when it is absent. The check is therefore strictly weaker for a
stranger than for the owner, which is the right way round: the owner is the one with
private names to leak.

**Tests are pytest run through `uv`**, per decision 9. The validation test shells out to
`claude plugin validate` and skips itself when the CLI is not on `PATH`, so the suite
stays green on a machine without Claude Code while still being the real check on the
owner's.

**`docs/smoke.md` is append-only, one section per change**, each with what it delivers,
the steps to run, and the result to expect. This change writes the file and its own first
section, which is also the template later changes copy.

## What setup and update write in a target project

**Nothing.** This change delivers no `setup` and no `update`, and installs no file into
any project. The only thing that lands on a machine is the plugin itself, inside Claude
Code's own plugin directory, which Claude Code owns and manages — the harness never
writes there and never reads it back. Project-file ownership starts in `C1c`, where
`/harnex:setup` writes the six files and records their hashes.

## Risks / Trade-offs

- **The manifest schema and its warnings evolve between Claude Code versions**, and
  `--strict` turns any new warning into a failure → the field list is minimal and the
  verified version (`2.1.267`) is recorded in `docs/smoke.md` with the check, so a
  failure after an upgrade is read as "the schema moved", not "the plugin broke". The
  "verified against" table in `C6` makes this systematic.
- **A plugin that contributes nothing looks broken to a user** who installs it and sees
  no command → the manual check in `docs/smoke.md` says in its first line that nothing is
  expected to appear, and the README's status line says the same.
- **The denylist's personal half is untracked**, so a fresh checkout runs the weaker
  check and could pass on a file the owner's run would reject → the check prints which
  half ran, and the owner's run is the gate before publishing.
- **The layout check hardcodes the directories Claude Code reads**, which is a list
  outside our control → it lives in one constant with the verified version beside it, and
  a new Claude Code directory is a one-line change.

## Open Questions

- Whether the catalogue will ever carry more than one plugin (a Codex-side guard was
  floated for later). Deferrable: adding an entry changes no requirement here.
- Whether `keywords` affects discovery anywhere today. Harmless either way.
