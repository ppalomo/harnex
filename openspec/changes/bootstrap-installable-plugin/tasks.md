## 1. The installable unit

- [x] 1.1 Create `plugin/.claude-plugin/plugin.json` with `name` (`harnex`), `version` (`0.1.0`), `description`, `author`, `homepage`, `repository`, `license` and `keywords`, and verify `claude plugin validate plugin --strict` exits 0 with no warning
- [x] 1.2 Create `.claude-plugin/marketplace.json` at the repository root with one plugin entry whose `source` is `./plugin`, plus `owner` and `metadata.description`, and verify `claude plugin validate . --strict` exits 0 with no warning
- [x] 1.3 Install from the checkout — `claude plugin marketplace add .` then `claude plugin install harnex@harnex` — and verify `/plugin` lists harnex with version `0.1.0` and that the session gains no command, skill, agent or hook

## 2. The five pillars

- [x] 2.1 Create `plugin/context/README.md` stating that pillar 1 holds the rule files, instruction templates and progress conventions, that it holds no enforcement and no technology name, and that `C1b` fills it
- [x] 2.2 Create `plugin/tools/README.md` stating that pillar 2 holds the MCP declarations and the stack profiles, that it is the only place a technology may be named, and that `C1c` and `C3` fill it
- [x] 2.3 Create `plugin/orchestration/README.md` stating that pillar 3 holds the workflow, the role prompts and the decision questions, that role prompts stay tool-agnostic, and that `C2` fills it
- [x] 2.4 Create `plugin/control/README.md` stating that pillar 4 holds the permissions, the shell guard and what always asks the human, that a deny never comes from a model alone, and that `C4` fills it
- [x] 2.5 Create `plugin/feedback/README.md` stating that pillar 5 holds the check command, the canary check and the decision journal, that every rule it enforces is stated in pillar 1, and that `C1d` fills it
- [x] 2.6 Verify each README names its pillar number, what belongs, what does not and the change that fills it, and that no README names a project or a technology outside pillar 2

## 3. The checks

- [x] 3.1 Add the test entry point (`tests/`, pytest run with `uv`) and a one-line instruction in `AGENTS.md` for running it, and verify `uv run --with pytest pytest -q` resolves pytest and loads the fixtures — with no test yet it reports the empty-suite code 5, so the entry point is green only once 3.2 lands
- [x] 3.2 Write the layout test: every directory under `plugin/` is a pillar or a directory Claude Code reads, and every pillar has its README; verify it passes on the tree and fails on a temporary stray directory and on a temporary pillar with its README removed
- [x] 3.3 Write the private-name test: a committed list of patterns that are private by construction, plus a personal list read from an environment variable and skipped when unset; verify it passes on the tree, reports which halves ran, and fails on a temporary file seeded with a matching pattern
- [x] 3.4 Write the manifest-validation test shelling out to `claude plugin validate` for both manifests, skipping itself when the CLI is absent; verify it passes with the CLI present and reports skipped when `PATH` hides it

## 4. The manual check

- [x] 4.1 Create `docs/smoke.md` with its purpose, the format every change appends (what it delivers, steps, expected result, the Claude Code version it was verified against), and the section for this change, recording `2.1.267`; verify the steps run top to bottom on a clean machine state and produce what the section says

## 5. Close the change

- [x] 5.1 Run the three checks and both validations once more on the final tree and verify all pass, with the private-name test reporting both halves ran
- [x] 5.2 Update `docs/PLAN.md` to match what landed — mark `C1a` delivered, record the verified Claude Code version and the two manifest fields strict requires — and verify `openspec validate --all` still passes
