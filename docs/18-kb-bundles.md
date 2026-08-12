# Portable KB Bundles — Federation, Part 1 (Design)

> Status: **proposed** (2026-08-12). First slice of the last unbuilt pillar:
> **federation / selective sharing beyond one instance** (old Tier-3
> deferral; `docs/06-roadmap.md` V2 #8's community loop points the same
> way). This part ships **offline federation**: export a KB as a
> self-contained JSON bundle, import a bundle on any knomms instance.
> Cross-instance protocols, provenance signatures, and quality signals
> stay in later parts. Proposed sprint: **v0.15.0 = KC-103–106**.

## 1. Problem

Everything shareable today stops at the instance boundary: visibility,
orgs, teams, and grants all assume one database. There is no way to hand a
colleague on another instance (or your future self on a rebuilt machine) a
knowledge base — the unit the whole platform revolves around. A portable
bundle is the smallest real federation: it needs no network protocol, no
identity exchange, no trust framework — a file is the API.

## 2. Why bundles before protocols

Live federation (subscribe to a remote KB, sync updates) needs instance
identity, auth handshakes, and conflict semantics — a multi-sprint design.
A bundle delivers the core value (knowledge moves between instances) with
none of that, works over any channel (email, USB, git-lfs), doubles as a
**backup/restore** mechanism, and its format becomes the wire format when
live federation arrives. Embeddings ship inside the bundle, so importing
is instant when the models match — the zero-external-cost invariant holds
even for compute.

## 3. Design decisions

| # | Decision | Call | Rationale |
|---|---|---|---|
| OQ-75 | Bundle format | Single JSON document: `{format: "knomms-kb-bundle", version: 1, exported_at, kb: {title}, sources: [{idx, type, title, description, raw_url}], chunks: [{source_idx, seq, locator, text, content_hash, is_overlap, embedding, embedding_model_id}]}` | Self-describing and diff-able; sources referenced by index (ids are instance-local and must not leak); JSON keeps part 1 dependency-free — compression is the transport's job |
| OQ-76 | Embeddings included | Yes, with their `embedding_model_id`. On import they are **kept** when the id matches the target KB's embed model, else nulled and re-embedded by the worker | The whole fleet runs nomic-embed-text-v1.5, so the common case imports with zero compute; the model check keeps the vector space honest if that ever changes |
| OQ-77 | Export scope + authz | `GET /v1/kbs/{kb_id}/export` — **owner-only 404** (not readable-relaxed). Chunks and source metadata only; no MinIO blobs, no learning paths/boards/notes/attempts | Export is bulk disclosure — a team/public reader can query a KB, but handing them every chunk verbatim as a file is a different grant; the owner decides. Learning/discovery artifacts are instance-social objects, out of scope (part 2 candidates) |
| OQ-78 | Import | `POST /v1/kbs/import` (multipart file, 200MB cap): validates format/version/caps, creates a **private** KB (fresh namespace, fresh ids), sources stamped `embedded` when their chunks carry usable embeddings, else `pending` + one `import.jobs` message re-embeds the namespace | Fresh ids everywhere — bundles are untrusted input, nothing in them may collide with instance state. Private-by-default mirrors every other creation path |
| OQ-79 | Validation caps | version == 1; ≤ 500 sources, ≤ 50 000 chunks, chunk text ≤ 20k chars; source `type` must be a known enum value else `plain_text`; embeddings must be 768 floats or null; everything else 422 with a precise reason | A bundle is attacker-controlled JSON — bound every axis before touching the DB. Unknown types degrade rather than reject so newer instances' bundles stay importable |
| OQ-80 | Re-embed worker | New `import.jobs` stream: `{kb_id, vector_namespace}` — batch-embeds chunks `WHERE namespace AND embedding IS NULL`, flips sources `pending → embedded` and the KB `building → ready` | Reuses `embed_chunks` and the stream idiom (`_STREAMS` dict); one job per import, not per chunk — the namespace is the unit of work |
| OQ-81 | Provenance | `description`-level only in part 1 (imported KB title is the bundle's; no schema change). Origin instance ids, signatures, fork-lineage across instances → part 2 | Provenance that can't be verified is decoration; signatures need instance identity, which is exactly what part 1 avoids |

## 4. Backend changes

- **New** `knowledge_base/bundles.py`:
  - pure `build_kb_bundle(kb_title, sources, chunks)` → dict (OQ-75; maps
    instance ids to indexes).
  - pure `validate_bundle(data)` → error string | None (OQ-79) and
    `plan_import(data, embed_model_id)` → normalized rows with a
    `needs_embedding` flag per source (OQ-76).
- Router: `GET /v1/kbs/{kb_id}/export` (owner-only via `get_by_id`;
  `Content-Disposition: attachment`), `POST /v1/kbs/import` (multipart;
  create KB + rows; commit **before** enqueue — the OQ-73 rule).
- Worker: `import.jobs` handler in `worker/import_embed.py`, registered in
  `_STREAMS`.
- Tests: bundle round-trip shape, validation matrix (caps, bad dims, bad
  version), plan (model match vs re-embed), id-freshness.

## 5. Frontend changes

- KB workspace: owner-only **Export** action (downloads the JSON via the
  BFF; plain link/`fetch`+blob).
- Dashboard KB section: **Import bundle** file input → POST multipart →
  navigate to the new KB; status via the existing KB card polling.

## 6. Non-goals (later federation parts)

- Live cross-instance sync, subscriptions, fork-lineage across instances
- Signatures / origin verification / community quality signals (OQ-81)
- Bundling learning paths, boards, notes, discussion (instance-social)
- MinIO blob export (upload originals) — chunks carry the text that matters

## 7. Verification plan (KC-106)

1. Unit: round-trip (export shape → validate → plan), caps matrix, model
   mismatch → needs_embedding, unknown source type degrades.
2. Live (Colima): export the video+web verify KB (owner 200, tester 404);
   import it back → new private KB, sources `embedded` immediately (model
   match), semantic search returns hits with preserved `ts:` locators,
   Q&A works; tamper a copy (bad dims / huge counts / wrong version) →
   422s; strip embeddings → import → `import.jobs` re-embeds → search
   works; 200MB cap rejects oversize.
3. Regression: full pytest; vue-tsc; existing KB flows untouched.
