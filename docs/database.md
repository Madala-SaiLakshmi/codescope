# Database

Tables: users, repositories (owner_id), analysis_jobs, source_files, symbols, dependency_edges, impact_reports, git_changes, impact_items, selected_tests.

- Snapshots: files, symbols and edges belong to an analysis job, so history is preserved and failures are isolated.
- Edges keep unresolved and external relationships (nullable target) for reports.
- Symbol names are indexed, not unique, because overloads and anonymous classes can collide.
- Migrations: Alembic (`alembic upgrade head`).