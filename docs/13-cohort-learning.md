# Cohort Learning, Part 1 — Design (V2 roadmap #1)

> Status: **proposed** (2026-08-06). First slice of the roadmap's highest-impact
> V2 priority (`docs/06-roadmap.md` §V2: "Cohort learning — unlocks the
> instructor persona fully; passage-anchored discussion, comprehension
> analytics, mastery gates"). This part ships **persisted attempts, owner
> analytics, and passage-anchored discussion**; mastery gates change the
> learner flow and stay in part 2. Design of record for the feature shape:
> `docs/03-learning-layer.md` §5.2/§5.4. Proposed sprint: **v0.10.0 =
> KC-080–086**, after v0.9.0 (`docs/12-harness-study-kb.md`).

## 1. Problem

Shared learning paths (v0.5.0) plus orgs/teams/grants (v0.6–0.7) mean several
learners already study the same published path — `concept_progress` is
per-(user, concept) by design. But the instructor persona is blind and mute:

- **Blind:** answer attempts are graded statelessly (`grade_attempt` returns a
  dict, persists nothing), and `completion_pct` is always the *requesting
  user's own* progress. A path owner cannot see who is stuck, which concepts
  fail, or which misconceptions recur — the exact analytics §5.4 promises.
- **Mute:** there is no discussion surface at all. §5.2's rule — every thread
  is anchored to a passage, no floating forums — has no schema behind it.

## 2. What "cohort" means here

No new entity. The spec's `cohort_id` sketch has no schema backing, and the
readability machinery already defines the audience: **the cohort of a path is
the set of users for whom `get_readable_path` returns it** (owner, or
published + readable KB via visibility/org/grants). Threads and analytics
reuse that predicate; join/leave/grant changes apply instantly, per OQ-10/13.

## 3. Design decisions

| # | Decision | Call | Rationale |
|---|---|---|---|
| OQ-37 | Attempt persistence | New `assessment_attempts` table (Migration 017): `item_id` FK CASCADE, `user_id`, `path_id` FK CASCADE (denormalised for cheap analytics scans), `answer_text` (as submitted), `correct` bool, `matched_distractor_id` (soft ref, nullable), `created_at`. No uniqueness — every attempt is a row. Recorded inside the existing attempt endpoint; response shape unchanged | Analytics cannot be backfilled — start recording now. Learners submit choice *text* (choice ids are per-user shuffle indexes), so text is the stable thing to store; the matched distractor carries the misconception label for aggregation |
| OQ-38 | `grade_attempt` scoping fix | Validate item ∈ concept ∈ path (the `_get_readable_concept_id` pattern) before grading; 404 otherwise | Pre-existing bug: the item is looked up by `(item_id, concept_id)` only, never checked against `path_id`. Today it leaks a grade across paths; with persisted rows it would attribute attempts to the wrong path — must land in the same ticket as persistence |
| OQ-39 | Analytics surface | Owner-only `GET /v1/learning-paths/{id}/analytics`: per-learner rows (handle, display name, learned/active-concept pct, attempt count, correct rate, last activity) + per-concept rows (learners-learned count, attempt count, correct rate, top wrong answers with misconception labels). Notes are **never** exposed — they are private by contract | Exactly §5.4's list, computed from `concept_progress` + `assessment_attempts` with plain aggregates. Owner-only 404 (non-leak). Learner identity is visible to the owner — the same information a classroom teacher has; private notes stay private |
| OQ-40 | Discussion shape | Two tables (Migration 017): `discussion_threads` (`concept_id` FK CASCADE, `passage_chunk_id` **soft** String(36) nullable, `passage_excerpt` snapshot, `created_by`, `title`, `body`, `created_at`) and `discussion_posts` (`thread_id` FK CASCADE, `user_id`, `body`, `created_at`). Anchoring optional-but-encouraged: a thread on a concept may cite one of that concept's `source_passages`; the excerpt is snapshotted at creation (chunks are soft-referenced and re-indexable) | §5.2's shape. Concept-level anchor keeps threads where learners are; the passage anchor + excerpt header gives "no floating discussion" without a hard FK the chunk lifecycle can't honour |
| OQ-41 | Discussion authz | Read + create thread/post: any user who can read the path (so drafts = owner only, published = the cohort). Delete: post author or path owner. Edit: not in part 1 | Reuses `get_readable_path`/`_get_readable_concept_id` exactly as notes/progress do — no new predicate. Owner moderation via delete is the minimum viable safety valve |
| OQ-42 | Ordering | Threads list newest-first (`created_at DESC`, the codebase convention); posts within a thread oldest-first (`created_at ASC`) | Replies read top-down; thread lists surface recent activity. The ASC exception is deliberate and documented here |
| OQ-43 | Denominator fix | `concept_count` on `LearningPathSummary` changes to count **non-pruned** concepts, matching `completion_pct`'s denominator | Today the card can show "5 concepts · 100% learned" when 2 are pruned and 3 learned. One truthful denominator everywhere |
| OQ-44 | No realtime | Discussion and analytics are plain request/response; no SSE/WS/poll | No realtime user-to-user precedent exists and none is needed to ship value; part 2 can revisit if cohorts get chatty |

## 4. Schema (Migration 017)

```
assessment_attempts (new)
  id                     String(36) PK
  item_id                String(36) NOT NULL REFERENCES assessment_items(id) ON DELETE CASCADE (indexed)
  path_id                String(36) NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE (indexed)
  user_id                String(36) NOT NULL REFERENCES users(id) (indexed)
  answer_text            Text NOT NULL
  correct                Boolean NOT NULL
  matched_distractor_id  String(36) NULL           -- soft ref; carries misconception label
  created_at             timestamptz NOT NULL

discussion_threads (new)
  id                String(36) PK
  concept_id        String(36) NOT NULL REFERENCES path_concepts(id) ON DELETE CASCADE (indexed)
  created_by        String(36) NOT NULL REFERENCES users(id)
  passage_chunk_id  String(36) NULL               -- soft ref (chunks are re-indexed)
  passage_excerpt   Text NOT NULL DEFAULT ''      -- snapshot taken at creation
  title             String(200) NOT NULL
  body              Text NOT NULL DEFAULT ''
  created_at        timestamptz NOT NULL

discussion_posts (new)
  id          String(36) PK
  thread_id   String(36) NOT NULL REFERENCES discussion_threads(id) ON DELETE CASCADE (indexed)
  user_id     String(36) NOT NULL REFERENCES users(id)
  body        Text NOT NULL
  created_at  timestamptz NOT NULL
```

`downgrade()` drops all three.

## 5. Backend changes

- `grade_attempt` (learning/service.py): concept-in-path validation (OQ-38),
  then grade as today, then insert an `AssessmentAttempt` row (distractor match
  already computed for feedback — reuse it for `matched_distractor_id`).
  Response schema unchanged.
- New analytics method + router endpoint (OQ-39): owner-only via `get_path`;
  aggregates with `GROUP BY` over `concept_progress` and `assessment_attempts`
  joined to users for handles; wrong-answer tops grouped by normalised
  `answer_text` with the matched distractor's `misconception_label`.
- New `learning/discussions.py` service (or extend LearningService):
  `list_threads(concept)`, `create_thread`, `get_thread_with_posts`,
  `create_post`, `delete_post` — all guarded by `_get_readable_concept_id`
  (+ author-or-path-owner for delete). Passage anchor validated against the
  concept's `source_passages` chunk ids; excerpt snapshotted server-side.
- Router: `GET/POST /v1/learning-paths/{pid}/concepts/{cid}/threads`,
  `GET /v1/learning-paths/{pid}/threads/{tid}` (with posts ASC),
  `POST .../threads/{tid}/posts`, `DELETE .../threads/{tid}/posts/{post_id}`.
- `LearningPathSummary.concept_count` → non-pruned count (OQ-43).
- Schemas: `AttemptResult` unchanged; new `ThreadOut/ThreadSummary/PostOut`
  (author as `{id, handle, display_name}`), `PathAnalyticsOut`.
- Tests (pure-logic suite constraint): wrong-answer aggregation and the
  analytics shaping extracted as pure functions; guard decision helpers where
  branching warrants it.

## 6. Frontend changes

- Learn page: extract `ConceptDiscussion.vue` — thread list (DESC) with
  passage-excerpt headers, thread view with posts (ASC), new-thread form with
  optional "anchor to passage" selector fed by the concept's source passages,
  reply box, delete on own posts (+ all posts for the path owner).
- Owner-only **Learners** panel (new tab or section on the learn page):
  per-learner table (progress %, attempts, correct rate, last activity) and
  per-concept table (learned count, correct rate, top misconceptions).
- `kb/[kbId]/learn` cards may show "N learners" from analytics later — not in
  part 1 (the list endpoint stays untouched).
- BFF: dedicated handlers per learning-route convention (ofetch, auth header
  forwarded).

## 7. Non-goals (part 2 candidates)

- Mastery gates / prerequisite enforcement (changes the learner flow)
- Editing posts, reactions, mentions, notifications
- Realtime updates (OQ-44)
- Cohort entities separate from path readability; enrolment lists
- Backfilling attempts (impossible — none were recorded)

## 8. Verification plan (KC-086)

1. Unit: attempt persistence + scoping 404 (cross-path item); aggregation
   helpers; thread guard decisions; denominator fix.
2. Live (Colima, two users same org): learner B attempts items on A's
   published path (some wrong, matching a distractor) → A's analytics shows
   B's progress, attempt counts, correct rate, and the misconception label;
   B opens a passage-anchored thread, A replies, B sees the reply; org-less
   user C gets 404 on threads and attempts for the same path; A's analytics
   404s for B. Draft-path threads visible to A only.
3. Regression: attempt response shape unchanged (learner UX identical);
   existing learn-page flows; full pytest; vue-tsc clean.
