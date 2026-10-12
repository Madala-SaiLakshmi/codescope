# API

All endpoints except health, register and login need `Authorization: Bearer <token>`. Interactive docs: `/docs`.

| Method | Path | Purpose |
|---|---|---|
| GET | /api/health, /api/health/db | liveness |
| POST | /api/auth/register, /api/auth/login | accounts (429 when rate limited) |
| GET | /api/auth/me | current user |
| POST/GET | /api/repositories | add / list own repositories |
| POST/GET | /api/repositories/{id}/analyses | start / list analyses |
| GET | /api/analyses/{id} | status |
| GET | /api/analyses/{id}/graph?level=type\|symbol | graph |
| GET | /api/analyses/{id}/dependencies, /dependents?symbol=&transitive= | lookups |
| POST/GET | /api/repositories/{id}/impact-reports | compare revisions / list |
| GET | /api/impact-reports/{id} | full report |

Errors: 401 unauthenticated, 404 missing or not yours, 409 conflict, 413 body too large, 422 invalid input, 429 rate limited.