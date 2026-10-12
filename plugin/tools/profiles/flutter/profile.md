# flutter

A Flutter application: Dart, Flutter, and the widget and integration test frameworks the
project declares.

## Check command

The project's own `AGENTS.md` names the single command that analyses, formats and runs
the test suite. This profile does not guess one — `flutter analyze` and `flutter test`
are the usual shape, but a builder that finds none declared asks rather than inventing a
target that may not exist. Where the project keeps a target that runs the integration
tests on a device or an emulator, `AGENTS.md` names that too; a test run full of skipped
tests is treated as no evidence at all, not as a passing check.

## Conventions

- State management and layering are the project's call, not the stack's: which approach
  holds state, where a screen's logic lives and what a widget may import, as `AGENTS.md`
  declares. A change that puts state or a rule somewhere the project did not declare is
  worth naming in a builder's report, not silently allowed.
- A screen is built from composable widgets, and each widget that a person can see or
  operate carries its `Semantics` story — a label, a role, a state — as part of its
  definition, not as an afterthought.
- A platform channel or a piece of native code is named in a builder's report, with the
  platform it binds to, never silently added — it is the one part of the tree the Dart
  toolchain cannot check.
- Theme tokens over literals: a colour, a text style or a spacing value comes from the
  project's `ThemeData` and its extensions, not from a literal in a widget.

## Tools expected

The Flutter SDK, Dart, and whatever the project's own `pubspec.lock` already names. The
state-management library, the test helpers and the linter rules are the project's — this
profile does not choose one.

## Verification evidence

The browser step `verify` runs for a UI profile does not apply here: a Flutter screen is
not a page a browser automation tool can drive, so this profile is deliberately not
listed in `ui.json` and no Playwright entry is proposed. In its place, `verify` reads the
project's own widget and integration tests, which `AGENTS.md` names, plus golden tests
where the project keeps them. A screen the change touches with no test of its own is a
gap in the evidence, and the verifier says so rather than counting the build as proof.

## Team

This profile is a directory, and each file beside this one is what this stack adds to one
specialist: `designer.md`, `accessibility-reviewer.md` and `security-reviewer.md`. A
project that chooses `flutter` gets those three agents, each rendered from the role of
the same name with the fragment appended, and nothing a fragment says alters the role.
