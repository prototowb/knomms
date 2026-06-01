"""Pure dataclasses for the curriculum agent — no SQLAlchemy imports.

Keeping these in a separate module (not in agent.py or service.py) preserves
the same import-isolation pattern established by retrieval/types.py:
tests import these without pulling in any DB machinery.
"""

from dataclasses import dataclass, field


@dataclass
class PassageDraft:
    chunk_id: str
    locator: str
    source_id: str
    text: str


@dataclass
class DistractorDraft:
    text: str
    why_wrong_chunk_id: str
    misconception_label: str | None = None


@dataclass
class AssessmentDraft:
    question_text: str
    correct_answer: str
    grounding_chunk_id: str
    distractors: list[DistractorDraft] = field(default_factory=list)


@dataclass
class ConceptProposal:
    title: str
    explanation_text: str
    passage_ids_cited: list[str]
    source_passages: list[PassageDraft]
    assessment: AssessmentDraft | None = None
