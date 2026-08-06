# Organisations — Design (supersedes OQ-3)

> Status: **shipped in v0.6.0** (2026-08-05, KC-060–064). §9 verification executed in full, all green.
> Scope: make `team` visibility mean *same organisation* instead of *all registered users on this instance*.

## 1. Problem

OQ-3 (v0.2.0) deliberately shipped `team` visibility as "all registered users on this
instance" because no `organisations` table existed. Every sharing feature since
(KB visibility, shared learning paths, asset/harness visibility) inherited that
equation, so today `team` and `public` are indistinguishable for reads by any
logged-in user. On a single-tenant hobby instance that's harmless; on a shared
instance (a company, a course, a community server) it makes `team` useless as a
boundary. This design gives `team` real meaning with the smallest schema and
API surface that doesn't paint us into a corner.

## 2. What the spec envisions vs. what we build now

`docs/05-platform-architecture.md` sketches organisations **and** team
memberships **and** per-resource ACLs (`CollectionACL`), with `org_id` +
`team_ids` JWT claims and namespace resolution at token issuance. None of that
machinery exists — `namespaces` is a single-element stub and authz is SQL
predicates on `owner_user_id` + `visibility`.

We build **only the organisation layer** now. Teams-within-an-org and ACLs
remain Tier 4 — the spec's layering (single `org_id` per user, plural
`team_ids`) is exactly why a single-org-per-user model doesn't block them:
multi-membership arrives later as a *teams* table, not by reworking orgs.

## 3. Design decisions

| # | Decision | Call | Rationale |
|---|---|---|---|
| OQ-6 | Membership model | Single optional org per user: `users.org_id` (nullable FK) + `users.org_role` (`admin\|member`) | Matches the spec's single `org_id` claim; no join table, no N-org read predicates. Multi-membership is the future *teams* concept, not orgs |
| OQ-7 | `team` semantics | `team` item readable iff owner and reader share a non-NULL `org_id`. Org-less users read no team items (and their own team items are effectively private to others) | The whole point of the feature; NULL≠NULL guard prevents "no org" becoming a giant shared org |
| OQ-8 | Backfill | Migration creates a **Default organisation** and assigns every existing user to it (creator = oldest user, as admin). New registrations start org-less | Preserves v0.5.x behaviour for existing content on day one (everyone kept team access they had); the operator renames/reshuffles at leisure. Tightening silently would break shared paths people already use |
| OQ-9 | Joining | Rotatable per-org `invite_code`; join by code. Any org-less user may create an org (becomes its admin) | Self-hosted, no email infra assumed. Codes are shareable out-of-band and revocable by rotation |
| OQ-10 | Enforcement point | SQL predicates using the request's loaded `User` row (`user.org_id`) — **no JWT changes** | `get_current_user` already does `db.get(User, sub)` per request, so org changes take effect immediately; the namespace-claim machinery the spec assumes isn't built and isn't needed for this |
| OQ-11 | Boards | Boards keep **no** team read relaxation (unchanged, deliberate since v0.5.0); board visibility stays `private\|public` in the UI | Boards are a publishing surface. Note: a board PATCHed to `team` via raw API mirrors that onto its KB (KC-058) — under this design that KB tightens from instance-readable to org-readable, which is strictly better |
| OQ-12 | `Source.visibility` | Still dormant. Do not touch | KB is the access boundary (v0.5.0 decision) |

## 4. Schema (Migration 013)

```
organisations
  id            String(36) PK (uuid)
  name          String(100) NOT NULL
  invite_code   String(36) NOT NULL UNIQUE   -- uuid4, rotatable
  created_by    String(36) FK users.id NOT NULL
  created_at    timestamptz NOT NULL server_default now()

users (add)
  org_id        String(36) FK organisations.id NULL, ON DELETE SET NULL, indexed
  org_role      String(10) NULL               -- 'admin' | 'member'; NULL iff org_id NULL
```

Backfill in `upgrade()`: insert Default organisation (`name='Default organisation'`,
`created_by` = oldest user by `created_at`) and `UPDATE users SET org_id=…,
org_role='member'` (creator gets `'admin'`). Skip entirely when `users` is empty
(fresh install). `downgrade()` drops the columns then the table.

Model registration: add `Organisation` to `app/models/__init__.py` **and**
`alembic/env.py` imports (both are manual — see backend conventions).

## 5. API surface (new domain `app/domains/organisations/`)

All routes require auth. Modular-monolith pattern: `service.py` + `router.py`
mounted at `/v1/orgs`, schemas in `app/schemas/organisation.py`.

| Route | Who | Behaviour |
|---|---|---|
| `POST /orgs` | org-less user | Create org `{name}`; caller becomes `admin`. 409 if already in an org |
| `GET /orgs/me` | member | Own org + member list `[{id, handle, display_name, org_role}]`. `invite_code` included **only for admins**. 404 if org-less |
| `POST /orgs/join` | org-less user | `{invite_code}` → join as `member`. 409 if already in an org, 404 bad code |
| `POST /orgs/leave` | member | Leave. Last admin must promote someone or be the last member (an org with members but no admin is refused with 409) |
| `POST /orgs/rotate-invite` | admin | New `invite_code`, returned once |
| `PATCH /orgs/members/{user_id}` | admin | `{org_role}` promote/demote. Cannot demote the last admin (409) |
| `DELETE /orgs/members/{user_id}` | admin | Remove member (their `org_id/org_role` → NULL). Admins cannot remove themselves (use leave) |

`UserOut` (`/auth/me`) gains `org_id` + `org_role` so the frontend knows which
surface to show. Registration flow unchanged — new users are org-less.

## 6. Read-path changes (the 7 sites + filters)

Add one shared helper (suggested home: `app/domains/organisations/predicates.py`)
so no read site hand-rolls the subquery:

```python
def team_or_public_clause(model, user) -> ColumnElement:
    """visibility == public, OR visibility == team AND owner is in the
    reader's org. Org-less readers get public only."""
    public = model.visibility == "public"
    if user.org_id is None:
        return public
    same_org_owner = model.owner_user_id.in_(
        select(User.id).where(User.org_id == user.org_id)
    )
    return or_(public, and_(model.visibility == "team", same_org_owner))
```

Rewire the access-check relaxations — every `visibility.in_(("team","public"))`:

- `knowledge_base/service.py:91` — `get_readable_by_id` (this transitively fixes KB workspace, sources, search, Q&A, source-status poll)
- `learning/service.py:107` — `_readable_kb_exists` (single call site; fixes shared learning paths)
- `harnesses/service.py:35,55,147` — get-readable, list, fork-source checks
- `assets/service.py:82,105` — get-readable, list

And the user-facing `?visibility=team` filter branches (`assets/service.py`,
`harnesses/service.py`): these narrow the base access predicate, so `team` now
means *team items I can read* — my own plus my org's. Org-less callers still
see their own team-marked items (they own them), just nobody else's.

`list_public()` (explore) and all board reads: untouched.

## 7. Frontend (MVP)

- **`/org` page** (auth-guarded): org-less → create form + join-by-code form;
  member → org name, member list, leave button; admin additionally → invite
  code with copy + rotate, promote/demote/remove controls. BFF routes under
  `server/api/orgs/` (import `ofetch` explicitly, per the Nitro stack-depth
  gotcha).
- **Nav**: link from the dashboard (e.g. next to the user handle), not a new
  top-nav item.
- **"Team" labels**: existing badges/selectors keep the word "Team"; where a
  tooltip is cheap, show "Team — visible to <org name>". No new shared
  component required (visibility UI is inline per page today; consolidating it
  is a separate refactor, don't couple it to this).
- Boards keep their two-option (`private|public`) visibility UI.

## 8. Non-goals (this sprint)

- Teams within an org, per-resource ACLs, viewer/editor roles (Tier 4, spec §CollectionACL)
- JWT `org_id`/`team_ids` claims and namespace resolution (not needed — OQ-10)
- Org-scoped *listing* endpoints ("browse my org's KBs") — explore stays public-only; can be a fast follow
- Email invites, multi-org membership, org avatars/profiles
- Plan/billing fields from the spec's JWT sketch

## 9. Verification plan (live, three users)

1. Users A + B in org X (A admin), user C org-less (register fresh; also proves org-less registration).
2. A sets a KB/asset/harness to `team` → B: 200 on KB + sources + search + Q&A, sees asset/harness in `?visibility=team`; C: 404 / empty.
3. Shared learning path on A's team KB: B can view/attempt/note/mark-learned; C cannot (404).
4. C joins via invite code → immediately gains team reads (no re-login — proves OQ-10). C leaves → immediately loses them.
5. Backfill check: pre-migration users land in Default organisation and keep reading each other's pre-existing team items.
6. Admin flows: rotate invite (old code 404s), promote B, demote-last-admin refused (409), remove member.
7. Regression: public items still readable by everyone incl. logged-out explore tabs; `pytest` 104+ green; `vue-tsc` clean.

## 10. Proposed ticket breakdown (v0.6.0)

| Ticket | Scope |
|---|---|
| KC-060 | Migration 013 + `Organisation` model + `users.org_id/org_role` + Default-org backfill + model registration |
| KC-061 | Organisations domain: service + router + schemas + `UserOut` extension; unit tests for the service guards (last-admin, 409s) |
| KC-062 | `team_or_public_clause` helper + rewire 7 read sites + 2 filter branches; unit tests for the predicate shapes |
| KC-063 | Frontend: `/org` page + BFF routes + dashboard link + team-badge tooltips |
| KC-064 | Live verification (three-user script above), docs sync (05-platform-architecture reality note, PROJECT_STATUS OQ table, CHANGELOG), release v0.6.0 |
