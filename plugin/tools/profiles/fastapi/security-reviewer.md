### Where input enters

Input reaches this stack through a route's signature: path and query parameters, a body
typed as a Pydantic model, headers and cookies, and every `Depends()` — a dependency that
reads a header or a cookie is where an identity claim enters, so follow it like any other
input. Pydantic guarantees shape and type, not meaning: a `str` field accepts a path
traversal, an `int` accepts a negative id, and a model without `extra="forbid"` drops
unknown fields silently rather than refusing them. Treat a value as constrained only where
a validator or a `Field` bound says so, and treat `UploadFile.filename` as the client's
choice, never as a path.

### What the stack guarantees, and what it does not

Authentication and authorisation are dependencies here, nothing else. A route is guarded
only by a dependency in its own signature, in its router's `dependencies=[...]`, or on the
app; a route in the diff with none, on a router that declares none, is unauthenticated,
and that is the shape of a missing check. A dependency that returns the current user but
is never compared to the resource's owner is the shape of a missing authorisation. The
SQLAlchemy query API binds its parameters; `text()` with a formatted string, or a raw
string handed to `execute()`, does not, so a request value reaching either is the
injection to follow. A `response_model` bounds what leaves; a route returning an ORM
object without one, or a model that carries a password hash, a token or an internal id,
leaks it.

### Stack-specific shapes to check

Settings loaded through `BaseSettings` read the environment; a default value on a
credential field puts a secret in the tree, and that is a finding whatever the value is.
`CORSMiddleware` with `allow_origins=["*"]` and `allow_credentials=True` lets any origin
act with the user's cookies. A `BackgroundTask` runs after the response, outside the
request's authentication and error handling, so what it does with request data is a path
of its own. A custom exception handler that echoes the exception's message returns
internals to the caller. None of this is the reviewer's code-quality ground: raise only
what an attacker could use.
