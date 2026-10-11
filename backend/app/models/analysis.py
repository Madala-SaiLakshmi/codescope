from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued|running|succeeded|failed
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    symbol_count: Mapped[int] = mapped_column(Integer, default=0)
    edge_count: Mapped[int] = mapped_column(Integer, default=0)


class SourceFile(Base):
    __tablename__ = "source_files"
    __table_args__ = (UniqueConstraint("job_id", "path", name="uq_source_files_job_path"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True
    )
    path: Mapped[str] = mapped_column(String(1000))
    language: Mapped[str] = mapped_column(String(20), default="java")
    content_hash: Mapped[str] = mapped_column(String(64))
    has_syntax_errors: Mapped[bool] = mapped_column(Boolean, default=False)


class Symbol(Base):
    __tablename__ = "symbols"
    __table_args__ = (Index("ix_symbols_job_qname", "job_id", "qualified_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True
    )
    file_id: Mapped[int] = mapped_column(
        ForeignKey("source_files.id", ondelete="CASCADE"), index=True
    )
    qualified_name: Mapped[str] = mapped_column(String(1000))
    name: Mapped[str] = mapped_column(String(300))
    kind: Mapped[str] = mapped_column(String(20))
    parent_qualified_name: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    start_line: Mapped[int] = mapped_column(Integer)
    end_line: Mapped[int] = mapped_column(Integer)


class DependencyEdge(Base):
    __tablename__ = "dependency_edges"
    __table_args__ = (
        Index("ix_edges_job_source", "job_id", "source_symbol_id"),
        Index("ix_edges_job_target", "job_id", "target_symbol_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True
    )
    source_symbol_id: Mapped[int] = mapped_column(
        ForeignKey("symbols.id", ondelete="CASCADE")
    )
    target_symbol_id: Mapped[int | None] = mapped_column(
        ForeignKey("symbols.id", ondelete="CASCADE"), nullable=True
    )
    relationship_type: Mapped[str] = mapped_column(String(20))  # extends|implements|calls|instantiates
    resolution_status: Mapped[str] = mapped_column(String(20))  # resolved|ambiguous|unresolved|external
    line: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(300))
