### Where input enters

Input reaches this stack through `params` — path segments, the query string and the body,
merged into one hash — and through headers, cookies and the session. Strong parameters
constrain shape, not meaning: a `permit` list that grows in the diff widens what a caller
may set, `permit!` permits everything, and a permitted `:role` or `:user_id` is mass
assignment of a field the caller should not own. A route constraint bounds a segment's
form, not its value. `send`, `public_send` or `constantize` on anything from `params`
lets the caller choose the method or the class, and that is the shape to follow first. A
file uploaded through Active Storage carries a client-chosen filename and content type;
treat both as the client's claim, never as a path or a reason to serve it inline.

### What the stack guarantees, and what it does not

Rails escapes HTML in views, binds the values Active Record's query API receives, and
checks a CSRF token on every non-`GET` request. Each guarantee has a shape that defeats
it: `html_safe` or `raw` on a value the caller shaped; a string interpolated into
`where`, `order`, `pluck` or `find_by_sql` rather than passed as a bind; a
`skip_before_action :verify_authenticity_token` on a controller the diff touches.
Authentication and authorisation are `before_action` filters here, nothing else: an
action in the diff on a controller with no such filter, or one named in a
`skip_before_action`, is unauthenticated, and that is the shape of a missing check. A
filter that loads the current user beside a query that never scopes to it —
`Model.find` rather than `current_user.models.find` — is the shape of a missing
authorisation.

### Stack-specific shapes to check

Secrets belong in `credentials.yml.enc` or the environment; a value of that kind in
`config/`, a fixture or an initializer is a finding whatever the value is. A parameter
name missing from `filter_parameters` reaches the log, and so does an exception message
that echoes one. A `redirect_to` with a caller-supplied URL and `allow_other_host: true`
sends the user anywhere. `Marshal.load`, `YAML.load` without `permitted_classes`, or a
`serialize` column whose coder is `Marshal` turns stored or supplied bytes into
behaviour. A `rescue_from` that renders the exception's message returns internals to the
caller. None of this is the reviewer's code-quality ground: raise only what an attacker
could use.
