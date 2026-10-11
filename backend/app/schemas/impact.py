from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ImpactCreate(BaseModel):
    base: str = Field(min_length=1, max_length=100)
    target: str = Field(default="HEAD", min_length=1, max_length=100)


class ImpactReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    base_revision: str
    target_revision: str
    base_sha: str | None
    target_sha: str | None
    base_job_id: int | None
    target_job_id: int | None
    status: str
    error_summary: str | None
    created_at: datetime
    completed_at: datetime | None
    changed_file_count: int
    changed_symbol_count: int
    affected_count: int
    uncertainty_count: int


class FileChangeRead(BaseModel):
    path: str
    old_path: str | None
    change_type: str


class ChangedSymbolRead(BaseModel):
    qualified_name: str
    kind: str
    path: str | None
    change: str | None


class AffectedSymbolRead(BaseModel):
    qualified_name: str
    kind: str
    path: str | None
    distance: int
    certain: bool
    root: str
    via: list[str]  # affected -> ... -> changed; each one depends on the next


class UncertaintyRead(BaseModel):
    path: str
    message: str


class ImpactReportDetail(ImpactReportRead):
    files: list[FileChangeRead]
    changed: list[ChangedSymbolRead]
    affected: list[AffectedSymbolRead]
    uncertainties: list[UncertaintyRead]


class SelectedTestRead(BaseModel):
    test_path: str
    test_class: str
    score: float
    confidence: str
    reasons: list[str]


class RiskFactorRead(BaseModel):
    name: str
    points: float
    max_points: float
    detail: str


class ImpactReportFull(ImpactReportDetail):
    risk_score: float | None = None
    risk_level: str | None = None
    risk_factors: list[RiskFactorRead] = []
    import_changes: list[UncertaintyRead] = []
    tests: list[SelectedTestRead] = []
