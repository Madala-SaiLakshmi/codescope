from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.engine.graph import DependencyGraph
from app.engine.resolver import Edge
from app.models.analysis import DependencyEdge, SourceFile, Symbol


class GraphQueryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def load(self, job_id: int) -> DependencyGraph:
        sym_rows = self.db.execute(
            select(Symbol, SourceFile.path)
            .join(SourceFile, Symbol.file_id == SourceFile.id)
            .where(Symbol.job_id == job_id)
        ).all()
        nodes = [
            {
                "qualified_name": s.qualified_name, "name": s.name, "kind": s.kind,
                "parent": s.parent_qualified_name, "path": path,
                "start_line": s.start_line, "end_line": s.end_line,
            }
            for s, path in sym_rows
        ]

        src, tgt = aliased(Symbol), aliased(Symbol)
        edge_rows = self.db.execute(
            select(DependencyEdge, src.qualified_name, tgt.qualified_name)
            .join(src, DependencyEdge.source_symbol_id == src.id)
            .join(tgt, DependencyEdge.target_symbol_id == tgt.id)
            .where(DependencyEdge.job_id == job_id)
        ).all()
        edges = [
            Edge(sq, tq, e.relationship_type, e.resolution_status, e.line, e.name)
            for e, sq, tq in edge_rows
        ]
        return DependencyGraph.from_records(nodes, edges)
