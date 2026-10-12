### Where the design surface lives

The tokens are the theme: `ThemeData`, its `ColorScheme` and `TextTheme`, and the
`ThemeExtension` subclasses the project adds for what Material does not name. A screen is
a widget tree, composed from the project's own widgets before the framework's, and a
component is a widget class with a constructor that says what varies. `MaterialApp` or
`CupertinoApp` sets the conventions a screen inherits — which one the project uses, and
whether it adapts per platform, is read from the tree, not chosen. Navigation is part of
the design: the router or `Navigator` routes already declared say how a screen is reached
and what it receives. Layout answers to the window, through `LayoutBuilder` and
`MediaQuery`, so a screen's shape at a phone width and at a desktop width are two states
of the same screen, not two screens. Read the theme, the shared widgets and the routes
the project already has before briefing, so that a new screen sits beside its neighbours.

### What the brief says, in this stack's terms

Name each screen as a widget tree: the route that reaches it, the arguments it takes, and
the widgets it is composed from, reused before new. Name each state as an explicit widget
state — what the tree shows when empty, loading, failed, partial or complete — and say
which widget owns the switch. Name each token the screens draw on as an entry of the
theme: an existing `ColorScheme` or `TextTheme` member they reuse, or a `ThemeExtension`
field they would need new. Name each component as a reusable widget with its constructor
parameters and its `Semantics` — the label it carries, the role it announces, the states
it tells without colour. Say where a screen follows the project's existing navigation and
layout patterns and where the proposal needs one the project does not yet have, as an
open question.

### What to raise rather than decide

Whether a screen looks Material on every platform or adapts to Cupertino where the app
runs there is a product decision → present both and what each costs in widgets and in
tests. The scope of an animation or a transition the proposal implies but does not
describe → name it and ask, since a motion the proposal did not ask for is a gap, not a
default. A layout the proposal needs at a width the project has no precedent for →
present the options with their cost.
