# Team Workspaces (V2 #4) — Delivery Audit

**Ticket:** KC-114 (v0.17.0 polish wave, OQ-91) · **Method:** read-only source + docs audit · **Date:** 2026-08-12
**Roadmap item:** `docs/06-roadmap.md` §V2 Priorities #4 — *"Team workspaces — collaborative knowledge bases for professional teams"*

---

## 1. What V2 #4 implies

The roadmap line is one sentence. Its concrete content comes from three other places: the MVP tables that deferred it (`docs/06-roadmap.md` — cross-cutting row *"Team workspaces — NO — V2"* and Layer 3 row *"Team-shared boards — NO — V2"*), the capability table in `docs/01-product-spec.md` §3 (*"Shared collections and knowledge bases for an organization; collaborative co-authorship"*), and the Research/Professional Team persona in §1.4. Read together, V2 #4 asks for:

1. **An organisation container** — membership, roles, a join mechanism, so "team" names a real boundary rather than "everyone on this instance."
2. **Team-scoped read access to a KB** — a corpus readable by colleagues and nobody else.
3. **Sub-org scoping** — share with *a subset* of the org (a squad, a cohort), not only all-or-nothing org-wide.
4. **Collaborative co-authorship of a KB** — more than one person can grow the corpus. Explicitly *not* simultaneous co-editing: §5 non-goals rules out *"real-time collaborative document editing… knowledge bases are collaborative, not simultaneous co-editors of a document."* Multi-writer, not multi-cursor.
5. **Team-shared collections (boards)** — §3 says "shared **collections** and knowledge bases"; the Layer 3 table lists *Team-shared boards* as its own deferred row.
6. **Authoring learning material from the shared corpus** — §1.4 flow 1–2: *"designate a subset of the team's shared knowledge base as the onboarding corpus"* then *"invoke the AI curriculum agent."*
7. **Enrolling colleagues as learners** with individual progress against the team's own runbooks — §1.4 flow 3, §2.2 *Cohort enrollment*.
8. **Discovery inside the org** — a member can find what the team has shared without a pasted link.
9. **Shared practitioner assets** — per `PROJECT_STATUS.md`, the AI Assets pillar is *"the practitioner layer for teams building with AI"*; prompt assets and harnesses are in scope for team collaboration, not just KBs.
10. **Corpus-change staleness propagation** — §1.4 flow 4. Adjacent: the roadmap defers this separately (Layer 2, *"requires event infrastructure"*).
11. **Isolated infrastructure for confidential corpora** — `docs/01-product-spec.md` §5 open question 3. Posed as a question, never promised.

Items 1–9 are the substance of V2 #4. Items 10–11 belong to other roadmap lines and are noted here only so the audit doesn't credit or blame #4 for them.

---

## 2. Already shipped

Everything in this section was live-verified, not merely coded: `scripts/verify-v070.sh` (37 checks, three users) covers the ACL layer end to end; `scripts/verify-v0100.py` / `verify-v0110.py` cover the multi-learner surfaces.

| Capability (from §1) | Delivered by | Where |
|---|---|---|
| Organisation container: create, join by rotatable invite code, leave, admin/member roles, member management | v0.6.0 KC-060/061, Migration 013 | `organisations/service.py`, `router.py`; `docs/09-organisations.md` OQ-6/OQ-9 |
| `team` visibility means *same organisation*, not *whole instance*; org-less readers get public only | v0.6.0 KC-062 (OQ-7) | `organisations/predicates.py:22` `team_or_public_clause` |
| Sub-org scoping: named teams within an org, multi-team membership | v0.7.0 KC-065/066, Migration 014 | `teams` / `team_memberships`; `/v1/orgs/teams` CRUD; OQ-14/OQ-15 |
| Per-resource ACL grants (viewer/editor) to a **user by handle** or a **team**, on KB / asset / harness | v0.7.0 KC-067, `acl_grants` | `acl/service.py`, `acl/router.py`; `predicates.py:40` `grant_subquery`, `:57` `readable_clause` |
| **Multi-writer KB** — a non-owner editor adds sources by URL and upload | v0.7.0 KC-067 (OQ-18) | `predicates.py:82` `editable_clause` → `knowledge_base/service.py` `get_editable_by_id` → `ingestion/service.py` |
| **Multi-writer assets** — a non-owner editor commits new versions | v0.7.0 KC-067 | `assets/service.py:235` |
| **Multi-writer harnesses** — editor adds/swaps slots, submits evals, reads the runs they triggered | v0.7.0 KC-067 | `harnesses/service.py:202,239,380` (writes), `:339,361` (reads) |
| Grants cover the whole KB chain transitively — sources, search, grounded Q&A, synthesis, shared learning paths | OQ-17 by design, one readability chain | `get_readable_by_id`, consumed by generation/synthesis/learning |
| Colleagues learn from a shared corpus: published-path view, attempts, private notes, learned marks — per-user progress | v0.5.0 KC-054 | `learning/service.py` `get_readable_path` |
| Cohort layer over shared corpora: persisted attempts, passage-anchored discussion, owner analytics with misconceptions | v0.10.0 KC-080–086, Migration 017 | `path_analytics`; `ConceptDiscussion.vue` |
| Mastery gates on shared paths: off/soft/hard, threshold, graph-aware locking, owner exempt | v0.11.0 + v0.16.0, Migrations 018/020 | `learning/gates.py` |
| Org discovery: "My organisation" explore tab (KBs, assets, harnesses) | v0.7.0 KC-068 (OQ-20) | `GET /v1/kbs/org`; explore tabs |
| Grantees can *find* what was shared: dashboard KB list unions granted KBs; asset/harness lists run `readable_clause` | v0.7.0 KC-067 | `list_for_user`; `assets/service.py:82,108` |
| Sharing UI: `ShareDialog` on all three grantable surfaces; Teams section on `/org`; team-badge tooltips | v0.7.0 KC-069 | `ShareDialog.vue`; kb/asset/harness pages; `/org` |
| Grant/revoke/join/leave immediate on unchanged tokens; org-leave cascades team memberships | OQ-10/OQ-13 (JWT rejected) | SQL enforcement in `predicates.py` |
| Visibility `private\|team\|public` on KB, asset, harness | v0.5.0–v0.6.0 | `VISIBILITIES` constants |
| Portable corpus handoff between instances (doubles as team backup/restore) | v0.15.0 KC-103–106 | KB export/import — owner-only |

**Net:** capabilities 1, 2, 3, 4, 7, 8, 9 from §1 are delivered. Capability 6 is delivered *for the KB owner only*. Capability 5 is deliberately not delivered.

---

## 3. Genuine gaps

### 3.1 A team editor cannot author a learning path on a KB they can write to — **the blocking gap**

**Missing.** `LearningService.create_stub` resolves the KB with the owner-only guard (`learning/service.py` `get_by_id`). An **editor** grantee can grow the corpus but cannot invoke the curriculum agent over it — exactly `docs/01-product-spec.md` §1.4 flows 1–2, the persona's own journey. Everything downstream of authoring already works for colleagues.

**Excluded by.** `PROJECT_STATUS.md` v0.5.0 *Known non-goals*: *"Team members cannot author learning paths on shared KBs."* Reaffirmed implicitly by OQ-18's enumerated editor surface.

**Size: M.**

**Invariant that makes it risky.** Path ownership is a *bundle*: publish, mastery-gate config, concept accept/prune/prerequisite editing, **and `path_analytics` — per-learner attempt data**. Naively relaxing the guard lets an editor acquire cohort surveillance over the KB owner's learners. Two viable shapes: (a) editor creates + publishes, analytics and gate config stay with the KB owner; (b) creator keeps the bundle, KB owner co-privileged. Either is a decision, not a patch.

### 3.2 Boards are not shareable with a team at all

No grants on boards, no team read, no org listing (every read owner-or-public). **Excluded by design** — OQ-11, reaffirmed as OQ-17/OQ-20 across two later sprints. **Size: M.** **Live inconsistency found:** `PATCH /boards/{id}` *accepts* `visibility="team"` and mirrors it onto the board's KB, but no board read honours `team` — write-accepted, read-dead. Either 422 it or implement the read.

### 3.3 Nothing can be removed from a shared corpus

No delete endpoint exists for KB, Source, Asset, or Harness — for anyone. A shared corpus is append-only. **Depended upon by** OQ-16 (`acl_grants` is FK-less *because* nothing deletes). **Size: M, easily underestimated** — the first delete must hand-clean grant rows and not strand `harness_study_docs` / `asset_source_projections` / `synthesis_source_projections` refs, plus MinIO objects.

### 3.4 Owner-only surfaces a co-owner plausibly needs

Metadata/visibility PATCH, asset→KB projection, bundle export, study-KB actions, grant management — all owner-only (OQ-18, deliberately). **Size: S each.** Only grant management is load-bearing (editor self-widening = escalation); bundle export's owner-only rationale (bulk disclosure ≠ read access, KC-103) should survive any widening.

### 3.5 No notification when something is shared with you

Deferred by `docs/10` §8; no notification layer exists anywhere. **Size: M** (a cross-cutting layer). Collaboration is silent — a real adoption drag for a workspace product.

### 3.6 No ownership transfer; exactly one owner forever

`docs/10` §2/§8 by design. **Size: S mechanically**, but: when an owner leaves the org, their `team`-visible resources go **dark to the org** (`team_or_public_clause` requires the owner to share the reader's org). A workspace whose creator leaves silently loses its corpus. "Who inherits" is org policy, not plumbing.

### 3.7 Grants take exact handles — no user search

`docs/10` §8. **Size: S.** The `/org` member list partially compensates.

### 3.8 Curriculum cannot be scoped to a subset of the corpus

§1.4 flow 1 says *subset*; generation runs whole-KB. Never scoped by any decision. **Size: S** — the plumbing exists (`retrieve()` source filter from KC-096, source multi-select from the Compare tab).

### 3.9 Adjacent, not V2 #4's debt

- Corpus-change staleness propagation — its own roadmap line ("requires event infrastructure"). L.
- Isolated infrastructure for confidential corpora — an open question the docs never promised. L.
- Granted-but-private items absent from the org tab — resolved by design (OQ-20: targeted shares, not org broadcasts).

---

## 4. Verdict

**Effectively done for the knowledge-base pillar — roughly 80% of V2 #4, and the strongest 80%.** v0.6.0/v0.7.0 shipped the whole hard part, live-verified across three users. V2 #4 was written before any of that existed and is now largely retrospective description.

Two genuine absences, of different kinds:

- **Boards (§3.2):** excluded by an explicit, thrice-reaffirmed decision — record as *out of scope for V2 #4*, but close the `visibility="team"` accept-then-ignore inconsistency either way.
- **Editor-authored learning paths (§3.1):** absent by omission — the one gap that blocks the persona V2 #4 names. Close it (with an explicit decision about the analytics/gate bundle) and "collaborative knowledge bases for professional teams" is delivered end to end.

**Recommended follow-ups, in order:**
1. One ticket for §3.1, gated on the path-owner-bundle decision (M). This is the closer.
2. Reject `visibility="team"` on boards (422) or implement the read — pick one (S); restate OQ-11 as out-of-scope for V2 #4.
3. ~~Fix the stale `get_by_id` docstring~~ — **done in this sprint** (it claimed ingest still used it; KC-067 moved ingest to `get_editable_by_id`).
4. §3.3 (deletes) and §3.6 (ownership transfer) will eventually be forced by real workspace use; neither blocks the roadmap line.
