from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.impact import GitChange, ImpactItem, ImpactReport, SelectedTest
from app.models.repository import Repository
from app.schemas.impact import (
    AffectedSymbolRead,
    ChangedSymbolRead,
    FileChangeRead,
    ImpactCreate,
    ImpactReportFull,
    SelectedTestRead,
    RiskFactorRead,
    ImpactReportRead,
    UncertaintyRead,
)
from app.services.impact_service import ImpactService

router = APIRouter(prefix="/api", tags=["impact"])


def _repo_or_404(db: Session, repository_id: int) -> None:
    if db.get(Repository, repository_id) is None:
        raise HTTPException(status_code=404, detail="Repository not found")


@router.post("/repositories/{repository_id}/impact-reports",
             response_model=ImpactReportRead, status_code=201)
def create_impact_report(repository_id: int, payload: ImpactCreate, db: Session = Depends(get_db)):
    _repo_or_404(db, repository_id)
    service = ImpactService(db)
    report = service.create_report(repository_id, payload.base, payload.target)
    return service.run(report.id)  # inline for now; becomes a background job later


@router.get("/repositories/{repository_id}/impact-reports",
            response_model=list[ImpactReportRead])
def list_impact_reports(repository_id: int, db: Session = Depends(get_db)):
    _repo_or_404(db, repository_id)
    stmt = (select(ImpactReport).where(ImpactReport.repository_id == repository_id)
            .order_by(ImpactReport.created_at.desc(), ImpactReport.id.desc()))
    return list(db.scalars(stmt))


@router.get("/impact-reports/{report_id}", response_model=ImpactReportFull)
def get_impact_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(ImpactReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Impact report not found")
    files = db.scalars(select(GitChange).where(GitChange.report_id == report_id)
                       .order_by(GitChange.id)).all()
    items = db.scalars(select(ImpactItem).where(ImpactItem.report_id == report_id)
                       .order_by(ImpactItem.id)).all()
    changed = [ChangedSymbolRead(qualified_name=i.qualified_name, kind=i.kind,
                                 path=i.path, change=i.change)
               for i in items if i.item_type == "changed"]
    affected = [AffectedSymbolRead(
                    qualified_name=i.qualified_name, kind=i.kind, path=i.path,
                    distance=i.distance or 0, certain=bool(i.certain),
                    root=i.root or "", via=list(i.via or []))
                for i in items if i.item_type == "affected"]
    base = ImpactReportRead.model_validate(report).model_dump()
    tests = db.scalars(select(SelectedTest).where(SelectedTest.report_id == report_id)
                       .order_by(SelectedTest.score.desc(), SelectedTest.id)).all()
    return ImpactReportFull(
        **base,
        files=[FileChangeRead(path=f.path, old_path=f.old_path, change_type=f.change_type)
               for f in files],
        changed=changed,
        affected=affected,
        uncertainties=[UncertaintyRead(**x) for x in (report.uncertainties or [])],
        risk_score=report.risk_score,
        risk_level=report.risk_level,
        risk_factors=[RiskFactorRead(**x) for x in (report.risk_factors or [])],
        import_changes=[UncertaintyRead(**x) for x in (report.import_changes or [])],
        tests=[SelectedTestRead(test_path=t.test_path, test_class=t.test_class, score=t.score,
                                confidence=t.confidence, reasons=list(t.reasons or []))
               for t in tests],
    )
