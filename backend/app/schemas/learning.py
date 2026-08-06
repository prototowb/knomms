from datetime import datetime

from pydantic import BaseModel


class DistractorOut(BaseModel):
    id: str
    text: str
    why_wrong_passage_id: str
    misconception_label: str | None = None

    model_config = {"from_attributes": True}


class ChoiceOut(BaseModel):
    id: str  # opaque post-shuffle index — never identifies the correct answer
    text: str


class AssessmentItemOut(BaseModel):
    id: str
    question_text: str
    # None for non-owner readers — shipping the answer to learners was a
    # pre-existing leak; graded server-side on attempt (KC-055)
    correct_answer: str | None = None
    grounding_passage_id: str
    distractors: list[DistractorOut] = []
    choices: list[ChoiceOut] = []

    model_config = {"from_attributes": True}


class ConceptGateOut(BaseModel):
    mastered: bool
    correct_items: int
    item_count: int


class PathConceptOut(BaseModel):
    id: str
    position: int
    title: str
    explanation_text: str
    explanation_passage_ids: list[str] = []
    source_passages: list[dict] = []
    instructor_annotation: str | None = None
    status: str
    assessment_items: list[AssessmentItemOut] = []
    # Mastery gating (docs/14) — gate is null when gating is off or the
    # requester owns the path; locked concepts are redacted in hard mode
    locked: bool = False
    gate: ConceptGateOut | None = None

    model_config = {"from_attributes": True}


class PathOwnerOut(BaseModel):
    id: str
    handle: str
    display_name: str

    model_config = {"from_attributes": True}


class LearningPathOut(BaseModel):
    id: str
    kb_id: str
    learning_goal: str
    status: str
    version: int
    time_budget_hours: float | None = None
    mastery_mode: str = "off"
    mastery_threshold: float = 0.8
    created_at: datetime
    updated_at: datetime
    concepts: list[PathConceptOut] = []
    learned_concept_ids: list[str] = []
    owner: PathOwnerOut | None = None

    model_config = {"from_attributes": True}


class LearningPathSummary(BaseModel):
    id: str
    kb_id: str
    learning_goal: str
    status: str
    version: int
    concept_count: int = 0
    learned_count: int = 0
    completion_pct: float = 0.0
    # Distinct users with progress or attempts — a count, never a roster (OQ-51)
    learner_count: int = 0
    mastery_mode: str = "off"
    created_at: datetime
    owner: PathOwnerOut | None = None

    model_config = {"from_attributes": True}


class ConceptNoteOut(BaseModel):
    id: str
    concept_id: str
    body: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpsertNoteRequest(BaseModel):
    body: str


class CreateLearningPathRequest(BaseModel):
    learning_goal: str
    time_budget_hours: float | None = None


class UpdateConceptRequest(BaseModel):
    status: str | None = None
    instructor_annotation: str | None = None


class UpdatePathRequest(BaseModel):
    mastery_mode: str | None = None
    mastery_threshold: float | None = None


class LearnerAnalyticsOut(BaseModel):
    user: PathOwnerOut
    learned_count: int
    completion_pct: float
    attempt_count: int
    correct_count: int
    correct_rate: float
    last_activity: datetime | None = None


class WrongAnswerOut(BaseModel):
    answer_text: str
    count: int
    misconception_label: str | None = None


class ConceptAnalyticsOut(BaseModel):
    concept_id: str
    title: str
    position: int
    learners_learned: int
    attempt_count: int
    correct_rate: float
    top_wrong_answers: list[WrongAnswerOut] = []


class PathAnalyticsOut(BaseModel):
    path_id: str
    active_concept_count: int
    learner_count: int
    learners: list[LearnerAnalyticsOut] = []
    concepts: list[ConceptAnalyticsOut] = []


class PostOut(BaseModel):
    id: str
    thread_id: str
    body: str
    author: PathOwnerOut | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ThreadSummaryOut(BaseModel):
    id: str
    concept_id: str
    title: str
    body: str
    passage_chunk_id: str | None = None
    passage_excerpt: str = ""
    author: PathOwnerOut | None = None
    post_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class ThreadOut(ThreadSummaryOut):
    posts: list[PostOut] = []  # oldest-first (OQ-42)


class CreateThreadRequest(BaseModel):
    title: str
    body: str = ""
    passage_chunk_id: str | None = None


class CreatePostRequest(BaseModel):
    body: str


class AttemptRequest(BaseModel):
    answer: str


class AttemptResult(BaseModel):
    correct: bool
    correct_answer: str | None = None
    grounding_passage_id: str
    feedback: str | None = None
