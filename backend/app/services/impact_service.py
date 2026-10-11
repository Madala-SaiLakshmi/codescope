import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.engine.graph import DependencyGraph
from app.engine.impact import compute_impact
from app.engine.resolver import Resolver
from app.models.analysis import AnalysisJob
from app.models.impact import GitChange, ImpactItem, ImpactReport
from app.models.repository import Repository
from app.parser.scanner import scan_java_files
from app.services.analysis_service import AnalysisService
from app.services.git_diff import export_revision, get_changes, resolve_revision
from app.services.git_service import (
    GitError,
    clone_repository,
    new_workspace,
    remove_workspace,
)

log = logging.getLogger(__name__)
HISTORY_DEPTH = 200


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ImpactService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_report(self, repository_id: int, base: str, target: str) -> ImpactReport:
        report = ImpactReport(
            repository_id=repository_id, base_revision=base,
            target_revision=target, status="queued",
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def run(self, report_id: int) -> ImpactReport:
        report = self.db.get(ImpactReport, report_id)
        repo = self.db.get(Repository, report.repository_id)
        report.status = "running"
        self.db.commit()

        settings = get_settings()
        workspace = new_workspace(Path(settings.workspace_dir))
        job_ids: list[int] = []
        try:
            if not repo.source_url:
                raise GitError("Repository has no source URL")
            clone = workspace / "repo"
            clone_repository(
                repo.source_url, clone, branch=repo.default_branch,
                timeout=settings.clone_timeout_seconds,
                max_bytes=settings.max_repo_mb * 1024 * 1024,
                depth=HISTORY_DEPTH,
            )
            base_sha = resolve_revision(clone, report.base_revision)
            target_sha = resolve_revision(clone, report.target_revision)
            export_revision(clone, base_sha, workspace / "base")
            export_revision(clone, target_sha, workspace / "target")

            base_job, base_scan, base_graph = self._analyze(
                repo.id, workspace / "base", base_sha, job_ids)
            target_job, target_scan, target_graph = self._analyze(
                repo.id, workspace / "target", target_sha, job_ids)

            changes = get_changes(clone, base_sha, target_sha)
            result = compute_impact(
                changes, target_scan.files, target_graph, base_scan.files, base_graph)
            return self._save(report, base_sha, target_sha, base_job, target_job, result)
        except (GitError, ValueError) as e:
            return self._fail(report_id, str(e), job_ids)
        except Exception:
            log.exception("Impact report %s failed", report_id)
            return self._fail(report_id, "Impact analysis failed", job_ids)
        finally:
            remove_workspace(workspace)

    # ---- internals ------------------------------------------------------

    def _analyze(self, repository_id: int, root: Path, sha: str, job_ids: list[int]):
        svc = AnalysisService(self.db)
        job = svc.create_job(repository_id)
        job_ids.append(job.id)
        svc._mark_running(job)
        scan = scan_java_files(root)
        edges = Resolver(scan.files).resolve()
        svc._persist(job, root, scan, edges, sha)  # one transaction per snapshot
        return job, scan, DependencyGraph.build(scan.files, edges)

    def _save(self, report, base_sha, target_sha, base_job, target_job, result) -> ImpactReport:
        for ch in result.changes:
            self.db.add(GitChange(report_id=report.id, path=ch.path[:1000],
                                  old_path=ch.old_path, change_type=ch.change_type))
        for c in result.changed:
            self.db.add(ImpactItem(
                report_id=report.id, item_type="changed", qualified_name=c.qualified_name,
                kind=c.kind, path=c.path, change=c.change))
        for a in result.affected:
            self.db.add(ImpactItem(
                report_id=report.id, item_type="affected", qualified_name=a.qualified_name,
                kind=a.kind, path=a.path, distance=a.distance, certain=a.certain,
                root=a.root, via=list(a.via)))
        report.base_sha, report.target_sha = base_sha, target_sha
        report.base_job_id, report.target_job_id = base_job.id, target_job.id
        report.uncertainties = [{"path": u.path, "message": u.message} for u in result.uncertainties]
        report.changed_file_count = len(result.changes)
        report.changed_symbol_count = len(result.changed)
        report.affected_count = len(result.affected)
        report.uncertainty_count = len(result.uncertainties)
        report.status = "succeeded"
        report.completed_at = _now()
        self.db.commit()  # report rows are saved together or not at all
        return report

    def _fail(self, report_id: int, message: str, job_ids: list[int]) -> ImpactReport:
        self.db.rollback()
        for jid in job_ids:
            job = self.db.get(AnalysisJob, jid)
            if job is not None and job.status in ("queued", "running"):
                job.status = "failed"
                job.error_summary = message[:500]
                job.completed_at = _now()
        report = self.db.get(ImpactReport, report_id)
        report.status = "failed"
        report.error_summary = message[:500]
        report.completed_at = _now()
        self.db.commit()
        return report
