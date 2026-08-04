from datetime import datetime

from pydantic import BaseModel


class DistractorOut(BaseModel):
    id: str
    text: str
    why_wrong_passage_id: str
    misconception_label: str | None = None

    model_config = {"from_attributes": True}


class AssessmentItemOut(BaseModel):
    id: str
    question_text: str
    correct_answer: str
    grounding_passage_id: str
    distractors: list[DistractorOut] = []

    model_config = {"from_attributes": True}


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


class AttemptRequest(BaseModel):
    answer: str


class AttemptResult(BaseModel):
    correct: bool
    correct_answer: str | None = None
    grounding_passage_id: str
    feedback: str | None = None
