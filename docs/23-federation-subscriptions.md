# Bundle Feeds & Subscriptions — Federation, Part 2 (Design)

> Status: **proposed** (2026-08-20). Part 1 (`docs/18-kb-bundles.md`) made
> knowledge portable as a file; this part makes it **flow**: an instance
> exposes a KB as a *bundle feed* (capability URL), another instance
> subscribes and re-syncs on demand. Pull-based, no instance identity, no
> push — the bundle format v1 is the wire format, exactly as OQ-75 planned.
> Signatures/origin verification and community quality signals need
> cross-instance identity and stay in part 3.
> Proposed sprint: **v0.19.0 = KC-119–122**.

## 1. Why pull + capability URLs

Cross-instance *identity* (keys, handshakes, trust decisions) is the
expensive half of federation. A capability URL — an unguessable slug the
owner mints and hands out — delivers selective sharing with zero identity
infrastructure: possession is the grant, rotation is revocation. Pull
(subscriber fetches when it wants) means no delivery queues, no retries, no
webhook auth. And critically for this project: the whole loop is
**live-verifiable on one host** — an instance subscribing to its own feed
URL exercises the identical HTTP path a remote peer would.

## 2. Design decisions

| # | Decision | Call | Rationale |
|---|---|---|---|
| OQ-95 | Feed exposure | Owner opt-in per KB: `POST /v1/kbs/{kb_id}/federation` mints a `federation_feeds` row (UNIQUE kb, `slug` = 43-char urlsafe token); `DELETE` revokes. **Unauthenticated** `GET /v1/federation/{slug}` serves the bundle and `GET /v1/federation/{slug}/meta` serves `{title, source_count, chunk_count, bundle_hash}` for cheap change detection. `bundle_hash` = sha256 of the canonically-serialized bundle. The slug grants read regardless of KB visibility — the capability IS the grant; rotate by revoke + re-mint | Feeds reuse `build_kb_bundle` verbatim (OQ-75's wire-format promise). Meta-first polling keeps unchanged syncs at one tiny request. Owner-only management mirrors export's bulk-disclosure rationale (OQ-77) — enabling a feed is *more* deliberate than export, not less |
| OQ-96 | Subscription | `POST /v1/federation/subscriptions {feed_url}`: server fetches meta then the bundle (httpx: http/https only, 30s timeout, 200MB cap, no redirects), runs `validate_bundle` (bundles stay attacker-controlled input — OQ-79's caps apply to *remote* data doubly), imports via the part-1 flow into a **new private KB**, records `federation_subscriptions {kb_id UNIQUE, feed_url, bundle_hash, last_synced_at}` | Everything hard is already built: validation, planning, model-match instant embeddings, the `import.jobs` re-embed path. The subscription row is just provenance + sync state. SSRF note: a self-hosted operator configures their own subscriptions; scheme/size/timeout caps are the proportionate guard, documented rather than over-blocked |
| OQ-97 | Sync | `POST /v1/federation/subscriptions/{id}/sync`: fetch meta; same `bundle_hash` → `{changed: false}` (one request, no writes). Changed → fetch bundle, validate, **full replace**: wipe the mirror KB's sources (chunks cascade — the study-KB-rebuild idiom), re-materialize from the new plan, keep the same `kb_id`/namespace so links, grants, and learning paths survive (concept `source_passages`/anchors are soft refs by long-standing design — they degrade gracefully, never break) | Incremental diff needs stable source identity across instances, which bundles don't carry (ids are deliberately stripped, OQ-75) — content-hash-based diffing is a part-3 refinement. Full replace is correct-by-construction and idempotent |
| OQ-98 | Mirrors are read-only | A KB with a subscription row rejects local source additions (`submit_url`/`submit_file` → 422 "read-only mirror — add sources on the origin instance"). Deleting the subscription frees the KB (it becomes an ordinary local KB) | Sync wipes local additions — silently losing user data is worse than a clear 422. The unsubscribe escape hatch means nothing is ever trapped |
| OQ-99 | Surface | KB workspace (owner): **Federate** panel — enable → copyable feed URL, revoke; mirror KBs show origin + last-synced + a **Sync** button. Dashboard: **Subscribe to feed** input beside Import | Feed URL is a secret-bearing capability — the UI says so where it's copied |

## 3. Schema (Migration 022)

```
federation_feeds (new)
  id          String(36) PK
  kb_id       String(36) NOT NULL UNIQUE REFERENCES knowledge_bases(id) ON DELETE CASCADE
  slug        String(64) NOT NULL UNIQUE (indexed)
  created_at  timestamptz NOT NULL

federation_subscriptions (new)
  id              String(36) PK
  kb_id           String(36) NOT NULL UNIQUE REFERENCES knowledge_bases(id) ON DELETE CASCADE
  owner_user_id   String(36) NOT NULL REFERENCES users(id)
  feed_url        Text NOT NULL
  bundle_hash     String(64) NOT NULL
  last_synced_at  timestamptz NOT NULL
  created_at      timestamptz NOT NULL
```

`downgrade()` drops both.

## 4. Backend changes

- **New domain** `domains/federation/` (service + router, registered in
  main.py under `/v1`).
- Shared materialization extracted so part-1 import and part-2
  subscribe/sync use one code path: `knowledge_base/bundle_io.py` —
  `materialize_plan(db, user_id, kb, plan)` (source+chunk row creation,
  status stamping, returns needs_embedding) and `wipe_kb_sources(db, kb)`;
  `import_kb` (router) refactored onto it.
- Feed endpoints per OQ-95 (`secrets.token_urlsafe(32)`; canonical hash =
  sha256 of `json.dumps(bundle, sort_keys=True, separators=(",", ":"))`).
- Subscription service per OQ-96/97: httpx fetch with caps; commit before
  any `import.jobs` enqueue (the OQ-73 rule); sync returns
  `{changed, source_count, chunk_count, reindexing}`.
- Mirror guard per OQ-98 in `IngestionService.submit_url/submit_file`.
- Pure seams + tests: `canonical_bundle_hash`, `check_feed_url` (scheme/
  shape), sync-decision helper (`should_sync(local_hash, remote_meta)`).

## 5. Frontend changes

- KB page: Federate panel (owner; enable/revoke, copy URL with a
  capability warning) and, for mirrors, an origin/last-synced line + Sync
  button; BFF handlers per convention.
- Dashboard: Subscribe-to-feed input beside Import bundle → navigates to
  the new mirror KB.

## 6. Non-goals (part 3 candidates)

- Push/webhooks, scheduled auto-sync (a cron on the operator's side works today)
- Signatures, origin verification, cross-instance identity, quality signals
- Incremental sync via content-hash diffing (OQ-97)
- Subscribing to non-knomms sources (RSS etc.)

## 7. Verification plan (KC-122)

1. Unit: hash canonicalization, feed-URL checks, sync decision,
   materialize/wipe seams if pure.
2. Live (single host, loop-back through the real nginx chain): enable a
   feed on the video+web KB → unauthenticated meta + bundle fetch work,
   slug unguessable, non-owner enable 404; subscribe to the own-instance
   feed URL → mirror KB created private, embedded instantly (model match),
   search works; sync with nothing changed → `{changed: false}`; add a
   source to the origin KB, re-sync → mirror gains it (fresh materialize);
   mirror add-source → 422; revoke feed → meta/bundle 404 and sync fails
   cleanly; unsubscribe → KB becomes ordinary (add-source works).
3. Regression: part-1 import unchanged after the bundle_io refactor; full
   pytest; vue-tsc.
