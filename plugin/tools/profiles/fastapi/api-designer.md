### Where the contract lives

What a caller sees is the `APIRouter` tree the application mounts: each router's `prefix`
and `tags`, and on each route its method, path, parameters, request model,
`response_model`, `status_code`, `responses` and `operation_id`. Read the routers the
project already mounts before briefing: the version carried in a prefix, the pagination
and filtering parameters already in use, and the error shape the `HTTPException` handlers
and any custom exception handlers already return are the precedent the brief has to sit
beside. Dependency-based authentication is part of the contract — which `Depends()` guards
a route says who may call it — and belongs in the brief as plainly as the path does.

### What the brief says, in this stack's terms

Name each resource as a router and a prefix. Name each operation as a method and a path,
with its path and query parameters, its request model, its `response_model`, the status
code it returns on success — `201` for a create, `204` for a delete with no body — and the
`HTTPException` status and detail shape it returns otherwise, or the handler it relies on.
Say where pagination and filtering follow the project's existing convention and where the
proposal needs one the project does not yet have, as an open question. Say whether a
response model change adds a field, which existing callers tolerate, or removes or retypes
one, which breaks every caller that reads it; and whether a new required field in a
request model breaks the callers already sending the old shape. Give each operation an
`operation_id` and a tag, so the generated OpenAPI document and any client generated from
it stay stable across the change. The architect writes `design.md` from this: the more
each item reads as a route decorator and a Pydantic model, the less is left to infer.
