import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.engine.resolver import Resolver
from app.models.analysis import AnalysisJob, DependencyEdge, SourceFile, Symbol
from app.models.repository import Repository
from app.parser.scanner import scan_java_files
from app.services.git_service import (
    GitError,
    clone_repository,
    new_workspace,
    remove_workspace,
)

log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_job(self, repository_id: int) -> AnalysisJob:
        job = AnalysisJob(repository_id=repository_id, status="queued")
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def run(self, job_id: int) -> AnalysisJob:
        """Clone the repository into a private workspace, analyze it, clean up."""
        job = self.db.get(AnalysisJob, job_id)
        repo = self.db.get(Repository, job.repository_id)
        self._mark_running(job)
        settings = get_settings()
        workspace = new_workspace(Path(settings.workspace_dir))
        try:
            if not repo.source_url:
                raise GitError("Repository has no source URL")
            dest = workspace / "repo"
            revision = clone_repository(
                repo.source_url, dest, branch=repo.default_branch,
                timeout=settings.clone_timeout_seconds,
                max_bytes=settings.max_repo_mb * 1024 * 1024,
            )
            return self.analyze_directory(job_id, dest, revision)
        except GitError as e:
            return self._fail(job_id, str(e))
        except Exception:
            log.exception("Analysis job %s failed", job_id)
            return self._fail(job_id, "Analysis failed")
        finally:
            remove_workspace(workspace)

    def analyze_directory(self, job_id: int, root: Path, revision: str | None = None) -> AnalysisJob:
        job = self.db.get(AnalysisJob, job_id)
        if job.status != "running":
            self._mark_running(job)
        try:
            scan = scan_java_files(root)
            edges = Resolver(scan.files).resolve()
            self._persist(job, Path(root), scan, edges, revision)
        except FileNotFoundError:
            return self._fail(job_id, "Repository directory not found")
        except ValueError as e:  # limits such as too many files
            return self._fail(job_id, str(e))
        except Exception:
            log.exception("Analysis job %s failed", job_id)
            return self._fail(job_id, "Analysis failed")
        return job

    # ---- internals ------------------------------------------------------

    def _mark_running(self, job: AnalysisJob) -> None:
        job.status = "running"
        job.started_at = _now()
        self.db.commit()

    def _fail(self, job_id: int, message: str) -> AnalysisJob:
        self.db.rollback()  # discard any half-written snapshot
        job = self.db.get(AnalysisJob, job_id)
        job.status = "failed"
        job.error_summary = message[:500]
        job.completed_at = _now()
        self.db.commit()
        return job

    def _persist(self, job, root: Path, scan, edges, revision) -> None:
        """Everything below is one transaction: all of it is saved or none of it."""
        rows = []
        for pf in scan.files:
            data = (root / pf.path).read_bytes()
            sf = SourceFile(
                job_id=job.id, path=pf.path,
                content_hash=hashlib.sha256(data).hexdigest(),
                has_syntax_errors=pf.has_syntax_errors,
            )
            self.db.add(sf)
            rows.append((pf, sf))
        self.db.flush()

        symbol_rows = []
        for pf, sf in rows:
            for s in pf.symbols:
                sym = Symbol(
                    job_id=job.id, file_id=sf.id, qualified_name=s.qualified_name,
                    name=s.name, kind=s.kind, parent_qualified_name=s.parent,
                    start_line=s.start_line, end_line=s.end_line,
                )
                self.db.add(sym)
                symbol_rows.append(sym)
        self.db.flush()

        ids: dict[str, int] = {}
        for sym in symbol_rows:
            ids.setdefault(sym.qualified_name, sym.id)

        edge_count = 0
        for e in edges:
            source_id = ids.get(e.source)
            if source_id is None:
                continue
            target_id = ids.get(e.target) if e.target else None
            if e.target and target_id is None:
                continue
            self.db.add(DependencyEdge(
                job_id=job.id, source_symbol_id=source_id, target_symbol_id=target_id,
                relationship_type=e.kind, resolution_status=e.status,
                line=e.line, name=e.name[:300],
            ))
            edge_count += 1

        job.status = "succeeded"
        job.revision = revision
        job.file_count = len(rows)
        job.symbol_count = len(symbol_rows)
        job.edge_count = edge_count
        job.completed_at = _now()
        self.db.commit()
