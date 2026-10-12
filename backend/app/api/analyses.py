from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, owned_job, owned_repository
from app import ratelimit
from app.database import get_db
from app.engine.graph import DependencyGraph
from app.models.analysis import AnalysisJob
from app.models.user import User
from app.schemas.analysis import (
    AnalysisRead,
    DependencyRead,
    GraphEdge,
    GraphNode,
    GraphRead,
)
from app.services.analysis_service import AnalysisService
from app.services.graph_query_service import GraphQueryService

router = APIRouter(prefix="/api", tags=["analyses"])


def _loaded_graph(db: Session, user: User, job_id: int) -> DependencyGraph:
    job = owned_job(db, user, job_id)
    if job.status != "succeeded":
        raise HTTPException(status_code=409, detail=f"Analysis is {job.status}")
    return GraphQueryService(db).load(job_id)


@router.post("/repositories/{repository_id}/analyses", response_model=AnalysisRead, status_code=201)
def start_analysis(repository_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    owned_repository(db, user, repository_id)
    ratelimit.heavy_limiter.check(f"user:{user.id}")
    service = AnalysisService(db)
    job = service.create_job(repository_id)
    return service.run(job.id)  # inline for now; becomes a background job later


@router.get("/repositories/{repository_id}/analyses", response_model=list[AnalysisRead])
def list_analyses(repository_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    owned_repository(db, user, repository_id)
    stmt = (
        select(AnalysisJob)
        .where(AnalysisJob.repository_id == repository_id)
        .order_by(AnalysisJob.created_at.desc(), AnalysisJob.id.desc())
    )
    return list(db.scalars(stmt))


@router.get("/analyses/{job_id}", response_model=AnalysisRead)
def get_analysis(job_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    return owned_job(db, user, job_id)


@router.get("/analyses/{job_id}/graph", response_model=GraphRead)
def get_graph(
    job_id: int,
    level: str = Query("symbol", pattern="^(symbol|type)$"),
    include_uncertain: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    graph = _loaded_graph(db, user, job_id)
    if level == "type":
        graph = graph.collapse_to_types()
    nodes = []
    for n in graph.nodes():
        a = graph.node_data(n)
        nodes.append(GraphNode(
            id=n, label=a["name"], kind=a["kind"], path=a.get("path"),
            start_line=a.get("start_line"), end_line=a.get("end_line"), parent=a.get("parent"),
        ))
    edges = [
        GraphEdge(source=u, target=v, kinds=kinds, status=status)
        for u, v, kinds, status in graph.edge_list()
        if include_uncertain or status == "resolved"
    ]
    return GraphRead(job_id=job_id, level=level, nodes=nodes, edges=edges)


def _related(db, user, job_id, symbol, transitive, include_uncertain, relation) -> DependencyRead:
    graph = _loaded_graph(db, user, job_id)
    if symbol not in graph.nodes():
        raise HTTPException(status_code=404, detail="Symbol not found in this analysis")
    if relation == "dependencies":
        fn = graph.transitive_dependencies if transitive else graph.dependencies
    else:
        fn = graph.transitive_dependents if transitive else graph.dependents
    return DependencyRead(
        symbol=symbol, relation=relation, transitive=transitive,
        include_uncertain=include_uncertain, items=sorted(fn(symbol, include_uncertain)),
    )


@router.get("/analyses/{job_id}/dependencies", response_model=DependencyRead)
def dependencies(
    job_id: int, symbol: str = Query(...), transitive: bool = False,
    include_uncertain: bool = True, db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _related(db, user, job_id, symbol, transitive, include_uncertain, "dependencies")


@router.get("/analyses/{job_id}/dependents", response_model=DependencyRead)
def dependents(
    job_id: int, symbol: str = Query(...), transitive: bool = False,
    include_uncertain: bool = True, db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _related(db, user, job_id, symbol, transitive, include_uncertain, "dependents")
