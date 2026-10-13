from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ImpactReport(Base):
    __tablename__ = "impact_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    base_revision: Mapped[str] = mapped_column(String(100))
    target_revision: Mapped[str] = mapped_column(String(100))
    base_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    base_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("analysis_jobs.id", ondelete="SET NULL"), nullable=True
    )
    target_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("analysis_jobs.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="queued")
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    changed_file_count: Mapped[int] = mapped_column(Integer, default=0)
    changed_symbol_count: Mapped[int] = mapped_column(Integer, default=0)
    affected_count: Mapped[int] = mapped_column(Integer, default=0)
    uncertainty_count: Mapped[int] = mapped_column(Integer, default=0)
    uncertainties: Mapped[list] = mapped_column(JSON, default=list)
    import_changes: Mapped[list] = mapped_column(JSON, default=list, server_default='[]')
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    risk_factors: Mapped[list] = mapped_column(JSON, default=list, server_default='[]')


class GitChange(Base):
    __tablename__ = "git_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("impact_reports.id", ondelete="CASCADE"), index=True
    )
    path: Mapped[str] = mapped_column(String(1000))
    old_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    change_type: Mapped[str] = mapped_column(String(20))


class ImpactItem(Base):
    __tablename__ = "impact_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("impact_reports.id", ondelete="CASCADE"), index=True
    )
    item_type: Mapped[str] = mapped_column(String(10))  # changed | affected
    qualified_name: Mapped[str] = mapped_column(String(1000))
    kind: Mapped[str] = mapped_column(String(20))
    path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    change: Mapped[str | None] = mapped_column(String(20), nullable=True)  # changed only
    distance: Mapped[int | None] = mapped_column(Integer, nullable=True)   # affected only
    certain: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    root: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    via: Mapped[list | None] = mapped_column(JSON, nullable=True)


class SelectedTest(Base):
    __tablename__ = "selected_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("impact_reports.id", ondelete="CASCADE"), index=True
    )
    test_path: Mapped[str] = mapped_column(String(1000))
    test_class: Mapped[str] = mapped_column(String(1000))
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String(10))  # high | medium | low
    reasons: Mapped[list] = mapped_column(JSON, default=list)
