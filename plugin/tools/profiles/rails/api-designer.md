### Where the contract lives

What a caller sees is `config/routes.rb`: each `resources` block and the actions it
keeps with `only:` or `except:`, how deep the nesting goes, the `namespace` or `scope`
that carries the version, and the `constraints` on a segment or a request. The response
is whatever serialises the record — a serializer class, a `jbuilder` template or an
`as_json` override — and the request is the strong-parameters method the action calls,
which is the one place the accepted shape is written down. Read the routes the project
already draws before briefing: the version in the path or the header, the pagination and
filtering parameters already in use, and the error shape the `rescue_from` handlers and
each `render json: ..., status:` already return are the precedent the brief has to sit
beside. A `before_action` that authenticates is part of the contract — which filters a
controller runs says who may call it — and belongs in the brief as plainly as the path.

### What the brief says, in this stack's terms

Name each resource as a `resources` entry with its path, its nesting and its namespace.
Name each operation as an action with its method and path, the parameters its strong-
parameters method permits, the serializer or template that renders it, the status it
returns on success — `:created` for a create, `:no_content` for a delete with no body —
and the status and error body it returns otherwise, or the `rescue_from` handler it relies
on. Say where pagination and filtering follow the project's existing convention and where
the proposal needs one the project does not yet have, as an open question. Say whether a
serializer change adds an attribute, which existing callers tolerate, or removes or
retypes one, which breaks every caller that reads it; and whether a newly required
parameter breaks the callers already sending the old shape. The architect writes
`design.md` from this: the more each item reads as a line of `routes.rb` and a
`permit` list, the less is left to infer.
