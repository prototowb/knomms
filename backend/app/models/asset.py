import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    asset_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # system_prompt | few_shot_set | eval_suite | chain_spec | tool_spec
    visibility: Mapped[str] = mapped_column(
        String(10), nullable=False, default="private"
    )  # private | team | public
    fork_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fork_lineage: Mapped[list[str]] = mapped_column(ARRAY(String(36)), nullable=False, default=list)
    forked_from_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    owner: Mapped["User"] = relationship("User", back_populates="assets")  # type: ignore[name-defined]
    forked_from: Mapped["Asset | None"] = relationship(
        "Asset", remote_side="Asset.id", foreign_keys=[forked_from_id]
    )
    versions: Mapped[list["AssetVersion"]] = relationship(
        "AssetVersion",
        back_populates="asset",
        cascade="all, delete-orphan",
        order_by="AssetVersion.version_num",
    )


class AssetVersion(Base):
    __tablename__ = "asset_versions"
    __table_args__ = (
        UniqueConstraint("asset_id", "version_num", name="uq_asset_versions_asset_id_version_num"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_num: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    model_pin: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )  # draft | active | deprecated
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    asset: Mapped["Asset"] = relationship("Asset", back_populates="versions")
    eval_cases: Mapped[list["EvalCase"]] = relationship(
        "EvalCase",
        back_populates="asset_version",
        cascade="all, delete-orphan",
        order_by="EvalCase.created_at, EvalCase.id",  # stable case numbering in eval runs/SSE
    )
    source_projections: Mapped[list["AssetSourceProjection"]] = relationship(
        "AssetSourceProjection", back_populates="asset_version", cascade="all, delete-orphan"
    )
    harness_slots: Mapped[list["HarnessAsset"]] = relationship(
        "HarnessAsset", back_populates="asset_version", cascade="all, delete-orphan"
    )


class Harness(Base):
    __tablename__ = "harnesses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    visibility: Mapped[str] = mapped_column(
        String(10), nullable=False, default="private"
    )  # private | team | public
    fork_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fork_lineage: Mapped[list[str]] = mapped_column(ARRAY(String(36)), nullable=False, default=list)
    forked_from_id: Mapped[str | None] = mapped_column(ForeignKey("harnesses.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    owner: Mapped["User"] = relationship("User", back_populates="harnesses")  # type: ignore[name-defined]
    forked_from: Mapped["Harness | None"] = relationship(
        "Harness", remote_side="Harness.id", foreign_keys=[forked_from_id]
    )
    assets: Mapped[list["HarnessAsset"]] = relationship(
        "HarnessAsset",
        back_populates="harness",
        cascade="all, delete-orphan",
        order_by="HarnessAsset.position",
    )
    eval_runs: Mapped[list["EvalRun"]] = relationship(
        "EvalRun", back_populates="harness", cascade="all, delete-orphan"
    )


class HarnessAsset(Base):
    __tablename__ = "harness_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    harness_id: Mapped[str] = mapped_column(
        ForeignKey("harnesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_version_id: Mapped[str] = mapped_column(
        ForeignKey("asset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    harness: Mapped["Harness"] = relationship("Harness", back_populates="assets")
    asset_version: Mapped["AssetVersion"] = relationship("AssetVersion", back_populates="harness_slots")


class EvalCase(Base):
    __tablename__ = "eval_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_version_id: Mapped[str] = mapped_column(
        ForeignKey("asset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    input: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    grading_strategy: Mapped[str] = mapped_column(
        String(20), nullable=False, default="exact_match"
    )  # exact_match | contains | llm_judge | regex
    grading_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    asset_version: Mapped["AssetVersion"] = relationship("AssetVersion", back_populates="eval_cases")


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    harness_id: Mapped[str] = mapped_column(ForeignKey("harnesses.id"), nullable=False, index=True)
    triggered_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    # Snapshot of the eval suite version used — harness is mutable (add/swap), this preserves reproducibility
    eval_suite_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("asset_versions.id"), nullable=True
    )
    model_pin: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued"
    )  # queued | running | completed | failed
    metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    harness: Mapped["Harness"] = relationship("Harness", back_populates="eval_runs")
    triggering_user: Mapped["User"] = relationship("User", back_populates="eval_runs")  # type: ignore[name-defined]


class AssetSourceProjection(Base):
    __tablename__ = "asset_source_projections"
    __table_args__ = (
        UniqueConstraint(
            "asset_version_id", "kb_id", name="uq_asset_source_projections_version_kb"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_version_id: Mapped[str] = mapped_column(
        ForeignKey("asset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kb_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    asset_version: Mapped["AssetVersion"] = relationship(
        "AssetVersion", back_populates="source_projections"
    )
