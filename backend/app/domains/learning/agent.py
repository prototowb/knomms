"""Curriculum agent — MVP: heading-heuristic grouping + Ollama generation.

No LangGraph at this stage: the MVP pipeline is strictly linear
(extract concept groups → generate explanation + MC per group), so a
plain async function is simpler and avoids an unneeded heavy dependency.
The spec (§8.3) explicitly permits "chunking + title-based heuristics
rather than semantic clustering" at MVP.
"""

import json
import logging
import re

from app.domains.learning.types import (
    AssessmentDraft,
    ConceptProposal,
    DistractorDraft,
    PassageDraft,
)

log = logging.getLogger(__name__)


async def _ollama_generate(prompt: str) -> str:
    # Deferred import so agent.py is importable without httpx in the test environment.
    # Tests monkeypatch this function directly.
    from app.domains.generation.ollama import generate

    return await generate(prompt)


_CONCEPT_PROMPT = """\
You are a curriculum agent. Based only on the source passages below, produce a grounded concept entry.

Rules:
- Every factual claim in the explanation must be cited using [SOURCE:{{chunk_id}}] notation.
- Only cite chunk_ids that appear in the passages below — never invent them.
- The question's correct_answer must be directly supported by the grounding_passage_id.
- Each distractor must be plausible but contradicted by why_wrong_passage_id.
- Respond ONLY with valid JSON matching this exact schema — no markdown, no prose outside the JSON.

SCHEMA:
{{
  "title": "short concept title (< 80 chars)",
  "explanation": "2–4 sentence explanation with inline [SOURCE:chunk_id] citations",
  "passage_ids_cited": ["chunk_id", ...],
  "question": {{
    "question_text": "the MC question",
    "correct_answer": "the correct answer text",
    "grounding_passage_id": "chunk_id that supports the correct answer",
    "distractors": [
      {{
        "text": "a plausible wrong answer",
        "why_wrong_passage_id": "chunk_id",
        "misconception_label": "optional short label"
      }}
    ]
  }}
}}

SOURCE PASSAGES:
{passages}

Produce the JSON concept entry now:"""


MAX_GROUP_PASSAGES = 8


def build_concept_groups(chunks: list[dict]) -> list[list[PassageDraft]]:
    """Group non-overlap chunk dicts into concept groups.

    A new group starts at (KC-074):
    - a source boundary — each Source contributes its own concept(s). This is
      the load-bearing rule: chunker output never contains "\\n\\n" (windows are
      rejoined with single spaces), so the heading heuristic below can never
      fire on real chunks, and without the source boundary every chunk in the
      KB collapsed into one group;
    - a heading change within a source (kept for extractors that emit
      separable headings);
    - the MAX_GROUP_PASSAGES cap, so a long source yields several bounded
      concepts instead of one prompt containing every passage.

    Callers must pass chunks ordered by (source_id, seq) — the worker's
    SELECT already does.
    """
    groups: list[list[PassageDraft]] = []
    current_source: str | None = None
    current_heading: str | None = None
    current_group: list[PassageDraft] = []

    for c in chunks:
        if c.get("is_overlap"):
            continue

        heading = _extract_heading(c["text"])
        passage = PassageDraft(
            chunk_id=c["id"],
            locator=c["locator"],
            source_id=c["source_id"],
            text=c["text"],
        )

        starts_new_group = (
            c["source_id"] != current_source
            or (heading is not None and heading != current_heading)
            or len(current_group) >= MAX_GROUP_PASSAGES
        )
        if starts_new_group:
            if current_group:
                groups.append(current_group)
            current_group = []
            current_source = c["source_id"]
            current_heading = heading

        current_group.append(passage)

    if current_group:
        groups.append(current_group)

    return groups


def _extract_heading(text: str) -> str | None:
    """Extract the heading prefix from a chunk's text if present.

    The chunker injects headings as "A > B\\n\\nBody text...".
    If the first paragraph is ≤ 120 chars and contains no sentence-ending
    punctuation, treat it as the heading label.
    """
    parts = text.split("\n\n", 1)
    if len(parts) == 2:
        candidate = parts[0].strip()
        if len(candidate) <= 120 and not re.search(r"[.!?]", candidate):
            return candidate
    return None


async def generate_concept_proposal(group: list[PassageDraft]) -> ConceptProposal | None:
    """Generate one ConceptProposal from a group of related passages.

    Returns None if Ollama returns unparseable JSON or all cited IDs are
    hallucinated (not present in the passage list).
    """
    valid_ids = {p.chunk_id for p in group}
    passages_block = "\n\n".join(
        f"[PASSAGE chunk_id={p.chunk_id} locator={p.locator}]\n{p.text}\n[/PASSAGE]"
        for p in group
    )
    prompt = _CONCEPT_PROMPT.format(passages=passages_block)

    try:
        raw = await _ollama_generate(prompt)
        data = _parse_json_response(raw)
    except Exception as exc:
        log.warning("Concept generation failed: %s", exc)
        return None

    if not data:
        return None

    cited = set(data.get("passage_ids_cited") or [])
    cited_valid = cited & valid_ids
    if not cited_valid:
        log.warning(
            "Agent cited no valid passage IDs; discarding concept '%s'", data.get("title")
        )
        return None

    q = data.get("question") or {}
    grounding_id = q.get("grounding_passage_id", "")

    distractors: list[DistractorDraft] = []
    for d in q.get("distractors") or []:
        distractors.append(
            DistractorDraft(
                text=d.get("text", ""),
                why_wrong_chunk_id=d.get("why_wrong_passage_id", grounding_id),
                misconception_label=d.get("misconception_label"),
            )
        )

    assessment: AssessmentDraft | None = None
    if q.get("question_text") and q.get("correct_answer") and grounding_id in valid_ids:
        assessment = AssessmentDraft(
            question_text=q["question_text"],
            correct_answer=q["correct_answer"],
            grounding_chunk_id=grounding_id,
            distractors=distractors,
        )

    return ConceptProposal(
        title=data.get("title") or _fallback_title(group),
        explanation_text=data.get("explanation") or "",
        passage_ids_cited=list(cited_valid),
        source_passages=group,
        assessment=assessment,
    )


async def generate_curriculum(
    groups: list[list[PassageDraft]],
) -> list[ConceptProposal]:
    """Run the curriculum agent over all concept groups sequentially.

    Sequential (not concurrent) to avoid saturating the Ollama instance —
    the same constraint that applies to the generation service semaphore.
    Returns only proposals with valid grounding citations.
    """
    proposals: list[ConceptProposal] = []
    for group in groups:
        proposal = await generate_concept_proposal(group)
        if proposal is not None:
            proposals.append(proposal)
    return proposals


def _parse_json_response(raw: str) -> dict | None:
    """Extract the first JSON object from a model response."""
    raw = raw.strip()
    # Strip markdown code fences if present
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(raw)  # type: ignore[return-value]
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())  # type: ignore[return-value]
            except json.JSONDecodeError:
                pass
    return None


def _fallback_title(group: list[PassageDraft]) -> str:
    if not group:
        return "Unknown concept"
    heading = _extract_heading(group[0].text)
    return heading if heading else f"Concept from {group[0].locator}"
