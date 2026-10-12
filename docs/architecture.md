# Architecture

Request flow: React page -> `services/api.ts` (adds the bearer token) -> FastAPI route -> dependency (`get_current_user`, ownership check) -> service -> parser/engine -> SQLAlchemy -> PostgreSQL -> JSON -> React.

- `app/api`: thin HTTP layer and validation (Pydantic).
- `app/services`: orchestration and transactions (`AnalysisService`, `ImpactService`, `git_service`, `git_diff`).
- `app/parser`: Tree-sitter Java parsing into plain dataclasses.
- `app/engine`: resolver, dependency graph, change mapping, impact, test selection, risk.
- Graph direction: `A -> B` means A depends on B; impact follows edges backwards.
- Analyses run inside the request today; a background worker is planned.