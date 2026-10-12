### Where input enters

Input reaches this stack through a deep link and the route arguments the router parses
from it — a screen that reads an id, a URL or a flag from its route is reading what any
app or web page on the device chose to send; through a platform channel, where the
native side's reply is a `dynamic` the Dart side casts; through a `TextField` and its
controller; and through remote configuration, which is a value fetched from a server and
acted on as if the app had written it. Follow each from where it is parsed to where it is
acted on, and treat it as constrained only where a parser or a check says so, not where
a type annotation does.

### What the stack guarantees, and what it does not

There is no SQL layer by default, so injection is rare here; what the stack has instead
is local storage through packages, and the package decides what a stored value protects
against — `SharedPreferences` is a plain file any process with the app's sandbox can
read, and a token there is a token on disk. Nothing compiled into the app is secret: a
`--dart-define` value, a key in a Dart constant and a file under `assets/` are all in the
bundle, and the bundle is in the hands of whoever installed it. A `String` from a
platform channel or a route is a string, nothing more; the type system guarantees the
shape of a model and nothing about who shaped it.

### Stack-specific shapes to check

A session token, a refresh token or a credential written to `SharedPreferences` or a
plain file, where the platform's secure storage was the alternative, is a finding
whatever the value is. A `badCertificateCallback` that returns `true`, or an
`HttpClient` whose `SecurityContext` trusts everything, disables certificate validation
for every request after it. A `WebView` with JavaScript enabled and a JavaScript channel
hands a page a way into the app; follow what the handler does with what the page sends. A
request body, a header or a response logged with `print` or a logger leaves the user's
data in the device log. A deep link parameter used as a URL to open, a path to read or an
id to act on without a check is a request from a stranger acted on as the user's. An
endpoint over `http` rather than `https`, or a cleartext exception added to the platform
config, carries the user's data in the clear. A permission requested in the platform
manifest beyond what the feature in the diff needs is reach the app does not need and
an attacker could use. None of this is the reviewer's code-quality ground: raise only
what an attacker could use.
