from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    status: str
    revision: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_summary: str | None
    file_count: int
    symbol_count: int
    edge_count: int


class GraphNode(BaseModel):
    id: str            # qualified name
    label: str
    kind: str
    path: str | None
    start_line: int | None
    end_line: int | None
    parent: str | None


class GraphEdge(BaseModel):
    source: str        # source depends on target
    target: str
    kinds: list[str]
    status: str        # resolved | ambiguous


class GraphRead(BaseModel):
    job_id: int
    level: str         # symbol | type
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class DependencyRead(BaseModel):
    symbol: str
    relation: str      # dependencies | dependents
    transitive: bool
    include_uncertain: bool
    items: list[str]
