from sqlalchemy import func, select

from app.models.analysis import AnalysisJob, Symbol
from app.models.repository import Repository
from app.services.analysis_service import AnalysisService
from app.services.graph_query_service import GraphQueryService
from tests.sample_repo import write_sample


def make_repo(db):
    repo = Repository(name="demo", source_type="git_url",
                      source_url="https://github.com/o/r", default_branch="main")
    db.add(repo)
    db.commit()
    return repo


def symbol_count(db, job_id):
    return db.scalar(select(func.count()).select_from(Symbol).where(Symbol.job_id == job_id))


def test_successful_analysis_persists_snapshot(db, tmp_path):
    write_sample(tmp_path / "src")
    repo = make_repo(db)
    service = AnalysisService(db)
    job = service.create_job(repo.id)
    result = service.analyze_directory(job.id, tmp_path / "src", "abc123")

    assert result.status == "succeeded" and result.revision == "abc123"
    assert result.file_count == 3
    assert result.symbol_count > 0 and result.edge_count > 0
    assert symbol_count(db, job.id) == result.symbol_count

    graph = GraphQueryService(db).load(job.id)
    assert graph.transitive_dependents("app.b.B.help()") == {"app.a.A.run()", "app.c.C.f()"}
    assert any(set(c) == {"app.a.A", "app.b.B"} for c in graph.collapse_to_types().cycles())


def test_failed_analysis_keeps_previous_result(db, tmp_path):
    write_sample(tmp_path / "src")
    repo = make_repo(db)
    service = AnalysisService(db)
    first = service.create_job(repo.id)
    service.analyze_directory(first.id, tmp_path / "src", "abc")
    before = symbol_count(db, first.id)

    second = service.create_job(repo.id)
    failed = service.analyze_directory(second.id, tmp_path / "missing")

    assert failed.status == "failed"
    assert failed.error_summary == "Repository directory not found"
    assert symbol_count(db, first.id) == before
    assert symbol_count(db, second.id) == 0
    latest_ok = db.scalar(
        select(AnalysisJob)
        .where(AnalysisJob.repository_id == repo.id, AnalysisJob.status == "succeeded")
        .order_by(AnalysisJob.id.desc())
    )
    assert latest_ok.id == first.id
