### Where to look

Accessibility in this stack is the semantics tree, and the diff shapes it through
`Semantics` and its `label`, `button`, `header` and similar flags; through the
`semanticsLabel` and `semanticLabel` parameters of `Text`, `Image` and `Icon`; through
`ExcludeSemantics` and `MergeSemantics`, which remove or fold nodes; through `Focus`,
`FocusTraversalGroup` and `FocusTraversalOrder`, which decide where a keyboard goes
next; and through `Tooltip`, which gives an icon-only control a name. Read every
custom widget's `build` for what it adds to that tree and what it leaves out, and read
the theme a colour or a text style comes from before judging it.

### What the framework provides by default

Material and Cupertino widgets carry their semantics: a `TextButton`, an `IconButton`
with a `tooltip`, a `Checkbox`, a `Switch` and a `TextField` announce their role, their
label and their state without the diff doing anything. The guarantee ends where the diff
builds its own control: a `GestureDetector`, an `InkWell` or a `Container` with a tap
handler is reachable by a finger and by nothing else unless the diff wraps it in
`Semantics` with `button: true` and a label, and gives it focus. Report as missing only
what the surrounding tree does not provide — a shared widget that already wraps its
child in `Semantics` is a name inherited, not a name absent.

### Stack-specific shapes to check

An `IconButton` or an `Icon` tap target without a `tooltip` or a `Semantics` label is a
control a screen reader announces as nothing. An `Image` without `semanticLabel`, or with
one that says the file name, is a picture nobody not looking at it is told about; a
decorative one is honest only when `excludeFromSemantics` says so. A custom widget that
tells selected, invalid or disabled through a colour from `ColorScheme` alone, with no
label or icon change, is a state told by colour. A fixed-height box, a `SizedBox` or a
`Container` with a height around text ignores `MediaQuery.textScaler` and clips the
person who enlarged their text. A contrast read from a `ColorScheme` pair — `onSurface`
on `surface`, `onPrimary` on `primary` — is suspected until measured, since the theme
the pair resolves to is not in the diff. A custom layout that places widgets by position
gives the keyboard an order that is the build order, not the visible one, unless a
`FocusTraversalGroup` says otherwise. A change of content with no `liveRegion: true` on
its `Semantics`, and no `SemanticsService.announce`, is a change nobody not looking at
the screen is told about.
