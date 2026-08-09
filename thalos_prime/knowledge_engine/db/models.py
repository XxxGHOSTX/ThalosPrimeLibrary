"""SQLAlchemy 2.0 ORM models for the Knowledge Engine.

All tables are prefixed with ke_ to avoid namespace collisions.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all Knowledge Engine ORM models."""


class SourceRecordORM(Base):
    """ORM model for source records."""

    __tablename__ = "ke_sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)


class SnapshotRecordORM(Base):
    """ORM model for snapshot records."""

    __tablename__ = "ke_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    content: Mapped[str] = mapped_column(Text, nullable=False)


class ArtifactRecordORM(Base):
    """ORM model for artifact records."""

    __tablename__ = "ke_artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))


class ClaimRecordORM(Base):
    """ORM model for claim records."""

    __tablename__ = "ke_claims"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))


class EvidenceSpanORM(Base):
    """ORM model for evidence spans."""

    __tablename__ = "ke_evidence_spans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    claim_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    span_text: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)


class ContradictionRecordORM(Base):
    """ORM model for contradiction records."""

    __tablename__ = "ke_contradictions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    claim_id_a: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    claim_id_b: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    contradiction_score: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class CoordinateRecordORM(Base):
    """ORM model for coordinate records."""

    __tablename__ = "ke_coordinates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    lineage_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    semantic_cluster: Mapped[int] = mapped_column(Integer, nullable=False)
    coordinate_hex: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))


class AuditLogRecordORM(Base):
    """ORM model for audit log records."""

    __tablename__ = "ke_audit_log"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
