import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kb_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    learning_goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    time_budget_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Mastery gating (docs/14, OQ-45) — off | soft | hard; threshold in (0, 1]
    mastery_mode: Mapped[str] = mapped_column(String(10), nullable=False, default="off")
    mastery_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)

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

    concepts: Mapped[list["PathConcept"]] = relationship(
        "PathConcept",
        back_populates="path",
        cascade="all, delete-orphan",
        order_by="PathConcept.position",
    )
    owner: Mapped["User"] = relationship("User")  # type: ignore[name-defined]  # noqa: F821


class PathConcept(Base):
    __tablename__ = "path_concepts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    path_id: Mapped[str] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )

    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)

    explanation_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Denormalized list of chunk_ids cited inline in explanation_text
    explanation_passage_ids: Mapped[list] = mapped_column(
        JSONB, nullable=True, default=list
    )
    # Denormalized passage excerpts for display (list of {chunk_id, locator, source_id, excerpt})
    source_passages: Mapped[list] = mapped_column(JSONB, nullable=True, default=list)

    instructor_annotation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | accepted | pruned

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    path: Mapped["LearningPath"] = relationship("LearningPath", back_populates="concepts")
    assessment_items: Mapped[list["AssessmentItem"]] = relationship(
        "AssessmentItem",
        back_populates="concept",
        cascade="all, delete-orphan",
    )


class AssessmentItem(Base):
    __tablename__ = "assessment_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    concept_id: Mapped[str] = mapped_column(
        ForeignKey("path_concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Soft FK to chunks.id — passage may be re-indexed; stored as string to survive re-indexing
    grounding_passage_id: Mapped[str] = mapped_column(String(36), nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    concept: Mapped["PathConcept"] = relationship("PathConcept", back_populates="assessment_items")
    distractors: Mapped[list["Distractor"]] = relationship(
        "Distractor",
        back_populates="item",
        cascade="all, delete-orphan",
    )


class Distractor(Base):
    __tablename__ = "distractors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    item_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_items.id", ondelete="CASCADE"), nullable=False, index=True
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Soft FK to chunks.id — which passage shows this is wrong
    why_wrong_passage_id: Mapped[str] = mapped_column(String(36), nullable=False)
    misconception_label: Mapped[str | None] = mapped_column(Text, nullable=True)

    item: Mapped["AssessmentItem"] = relationship("AssessmentItem", back_populates="distractors")


class ConceptProgress(Base):
    """A learner marked a concept as learned — one row per (user, concept)."""

    __tablename__ = "concept_progress"
    __table_args__ = (UniqueConstraint("user_id", "concept_id", name="uq_concept_progress_user_concept"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    concept_id: Mapped[str] = mapped_column(
        ForeignKey("path_concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    learned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class AssessmentAttempt(Base):
    """One graded answer submission (docs/13, OQ-37) — every attempt is a row.

    path_id is denormalised (derivable via item → concept → path) so owner
    analytics can scan a path's attempts without a double join. answer_text is
    the submitted text (choice ids are per-user shuffle indexes and unstable);
    matched_distractor_id is a soft ref carrying the misconception label.
    """

    __tablename__ = "assessment_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    item_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    path_id: Mapped[str] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    matched_distractor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class DiscussionThread(Base):
    """Passage-anchored discussion thread on a path concept (docs/13, OQ-40).

    passage_chunk_id is a soft ref (chunks are re-indexed); passage_excerpt is
    snapshotted at creation so the thread header survives re-indexing. Threads
    without an anchor are allowed but the UI encourages anchoring (§5.2's
    "no floating discussion" rule).
    """

    __tablename__ = "discussion_threads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    concept_id: Mapped[str] = mapped_column(
        ForeignKey("path_concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    passage_chunk_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    passage_excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    author: Mapped["User"] = relationship("User")  # type: ignore[name-defined]  # noqa: F821
    posts: Mapped[list["DiscussionPost"]] = relationship(
        "DiscussionPost",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="DiscussionPost.created_at, DiscussionPost.id",  # replies read top-down (OQ-42)
    )


class DiscussionPost(Base):
    __tablename__ = "discussion_posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    thread_id: Mapped[str] = mapped_column(
        ForeignKey("discussion_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    thread: Mapped["DiscussionThread"] = relationship("DiscussionThread", back_populates="posts")
    author: Mapped["User"] = relationship("User")  # type: ignore[name-defined]  # noqa: F821


class ConceptNote(Base):
    """Private learner note on a path concept — one per (user, concept)."""

    __tablename__ = "concept_notes"
    __table_args__ = (UniqueConstraint("user_id", "concept_id", name="uq_concept_notes_user_concept"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    concept_id: Mapped[str] = mapped_column(
        ForeignKey("path_concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
