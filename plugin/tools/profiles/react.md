# react

A frontend on React, with whatever component library and styling approach the project's
own `AGENTS.md` names.

## Check command

The project's own `AGENTS.md` names the single command that lints, type-checks, and runs
the test suite. This profile does not guess one — a builder that finds none declared asks
rather than inventing a target that may not exist.

## Conventions

- Component boundaries are declared by the project, not assumed: which components own
  state, which are purely presentational, and where data fetching lives. A change that
  blurs a boundary `AGENTS.md` did not declare is worth naming in a builder's report.
- A design decision (spacing, color, typography) traces to the project's own design
  system or tokens where one exists, rather than a value picked by eye.
- Accessibility is not optional ceremony: interactive elements are reachable by keyboard
  and named for assistive technology, whatever the project's own component library
  provides for it.

## Tools expected

React. The specific bundler, component library, and test runner are whatever the
project's own lockfile already names — this profile does not choose one.
