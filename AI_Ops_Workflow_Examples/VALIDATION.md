# Validation

Validated during creation:

- Syntax of every Python file.
- `--help` on all nine numbered entry points.
- Workflow against an in-memory MongoDB test double: seed, duplicate seed, scoped injection, correlation aggregation, saved retrieval evidence, diagnosis state, approval gate, canary, recovery, repeated recovery, original-history preservation, and isolation of a second run.
- Embedding-response ordering and dimensions using a stubbed HTTP response.
- Reuse of unchanged knowledge documents without additional embedding requests.
- Legacy OpenAI request construction and response handling using a stubbed response.
- Provider usage aggregation.

No live Atlas cluster or provider credentials were supplied. Vector Search, search-index APIs, change streams, actual model access, network permissions, and live provider responses have not been validated end to end. Test doubles do not establish production server compatibility or concurrency guarantees.

Only trusted, bundled fixture source is executed for the recovery canary. Recovery writes synthetic state; it does not call real deployment or communication services.
