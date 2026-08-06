# Teams & Per-Resource ACLs — Design (Tier 4, part 1)

> Status: **proposed** (2026-08-06). Covers four of the five Tier 4 candidates from
> `docs/09-organisations.md` §8: teams-within-orgs, per-resource ACLs (viewer/editor),
> JWT namespace claims (assessed and rejected — OQ-13), and org-scoped explore
> listings. The fifth candidate (cloud eval adapter) is `docs/11-cloud-eval-adapter.md`.
> Proposed sprint: **v0.7.0 = KC-065–070**.

## 1. Problem

v0.6.0 gave `team` visibility real meaning (same organisation), but sharing is
still all-or-nothing at the org level: an item is private, org-wide, or public.
There is no way to share a specific KB with a specific person or a subset of the
org, and no way to let anyone but the owner *write* (add sources, commit asset
versions, run harness evals). Separately, org members have no way to *discover*
what their org has shared — explore is public-only, so "team" items are only
reachable by pasted links.

## 2. What the spec envisions vs. what we build now

`docs/05-platform-architecture.md` §4 sketches `CollectionACL(collection_id,
principal_type, principal_id, permission)` with viewer/editor/owner levels, plural
`team_ids` JWT claims, and namespace resolution at token issuance. We build the
teams table and a generalized grants table now, keep enforcement in SQL
predicates (OQ-13 below), and skip claims entirely. "Owner" is not a grantable
permission — ownership stays a column (`owner_user_id`), exactly one owner.

## 3. Design decisions

| # | Decision | Call | Rationale |
|---|---|---|---|
| OQ-13 | JWT `org_id`/`team_ids`/namespace claims | **Rejected — keep SQL-predicate enforcement (OQ-10 reaffirmed)** | The claim scheme presumes a gateway in front of separate services; we are a monolith where `get_current_user` loads the `User` row per request. Claims would reintroduce up-to-15-min staleness on join/leave/grant — immediacy on unchanged tokens is live-verified v0.6.0 behaviour. Teams make claims *staler* (membership churn), not safer. Today's `namespaces` claim is a stub read nowhere (`identity/service.py:73`, consumed only into an unused `user._namespaces`). Revisit only if Retrieval becomes a separately deployed service |
| OQ-14 | What a team *is* | Named subset of one org's members; **ACL principal only** — no new visibility enum value | `team` visibility keeps meaning "whole org" (renaming the enum is churn for nothing). Finer scoping is expressed as a grant to a team. Multi-team membership allowed — this is the spec's plural `team_ids`, arriving as a table, not a claim |
| OQ-15 | Team management | Any org member may create a team; team creator + org admins manage it (rename, add/remove members, delete). Members must belong to the same org | Self-serve, consistent with "any org-less user may create an org" (OQ-9). Org admins as co-managers avoids orphaned teams |
| OQ-16 | Grant table shape | One polymorphic `acl_grants(resource_type, resource_id, principal_type, principal_id, permission)`; `permission ∈ {viewer, editor}`, editor implies viewer; UNIQUE per (resource, principal) | One table → one predicate helper and one service, mirroring how `team_or_public_clause` kept v0.6.0 small. Cost: no FK on `resource_id` — acceptable because none of the three resource types has a delete endpoint today (assets deprecate); service-level cleanup documented for when one grows one |
| OQ-17 | Which resources | KBs, assets, harnesses. **Boards stay excluded** (OQ-11 holds — publishing surface, `private\|public`) | KB is the access boundary (v0.5.0), so KB grants transitively cover sources, search, Q&A, and shared learning paths through the existing readability chain. Learning paths get no grants of their own |
| OQ-18 | What `editor` unlocks | KB: add sources (URL + upload). Asset: commit new versions. Harness: add/swap slots, submit evals (and read the runs they can now trigger). Everything else — visibility, metadata PATCH, deprecate, fork-source rights, grant management — stays owner-only | Narrow, enumerated write surface via a `get_editable_by_id` twin of `get_readable_by_id` per domain. Grant management itself is owner-only so an editor cannot escalate |
| OQ-19 | Grant principals & reach | Principals: `user` (any user on the instance, resolved by handle) or `team` (own org's teams only). Direct user grants survive the grantee leaving an org; team grants die with team membership (cascade) | User grants are explicit person-to-person sharing — cross-org by nature on a shared instance. Team grants derive from membership, so they must follow it |
| OQ-20 | Org-scoped explore | "My organisation" tab on `/explore` (shown only to org members): team-visible KBs/assets/harnesses owned by org members. Boards excluded (OQ-11). Public/logged-out explore untouched | The §8 fast follow. Semantics = exactly what `?visibility=team` already returns for assets/harnesses since KC-062; only KBs need a new backend listing. Granted-but-private items do *not* appear here — grants are targeted shares, not org broadcasts |

## 4. Schema (Migration 014)

```
teams
  id            String(36) PK (uuid)
  org_id        String(36) FK organisations.id NOT NULL, ON DELETE CASCADE, indexed
  name          String(100) NOT NULL           -- UNIQUE (org_id, name)
  created_by    String(36) FK users.id NOT NULL
  created_at    timestamptz NOT NULL server_default now()

team_memberships
  team_id       String(36) FK teams.id NOT NULL, ON DELETE CASCADE
  user_id       String(36) FK users.id NOT NULL, ON DELETE CASCADE, indexed
  added_by      String(36) FK users.id NOT NULL
  created_at    timestamptz NOT NULL server_default now()
  PK (team_id, user_id)

acl_grants
  id             String(36) PK (uuid)
  resource_type  String(10) NOT NULL            -- 'kb' | 'asset' | 'harness'
  resource_id    String(36) NOT NULL            -- polymorphic, no FK (OQ-16)
  principal_type String(10) NOT NULL            -- 'user' | 'team'
  principal_id   String(36) NOT NULL
  permission     String(10) NOT NULL            -- 'viewer' | 'editor'
  granted_by     String(36) FK users.id NOT NULL
  created_at     timestamptz NOT NULL server_default now()
  UNIQUE (resource_type, resource_id, principal_type, principal_id)
  INDEX (principal_type, principal_id)
  INDEX (resource_type, resource_id)
```

No backfill — all three tables start empty; fresh installs and upgrades behave
identically. Migration `revision = "014"`, `down_revision = "013"`, hand-written
with full `downgrade()` (drop in reverse order), following `013_organisations.py`.

Models live in `app/models/team.py` + a `AclGrant` model in `app/models/acl.py`;
register both in `app/models/__init__.py` (import order after `organisation`/`user`).
`alembic/env.py` picks them up transitively via the package import.

**Org-membership cascades (service-level, not schema):** `OrganisationService.leave`
and `remove_member` must also delete the user's `team_memberships` rows in that
org's teams (their `org_id` goes NULL, so staying in a team would leak team-grant
access). DB cascades only cover user/org *deletion*.

## 5. API surface

### Teams — extend `app/domains/organisations/` (service + router share the org domain; mounted under `/v1/orgs`, so the existing BFF catch-all covers everything)

| Route | Who | Behaviour |
|---|---|---|
| `POST /orgs/teams` | org member | Create `{name}`; caller becomes creator. 409 duplicate name in org |
| `GET /orgs/teams` | org member | Own org's teams `[{id, name, member_count, is_member, can_manage}]` |
| `GET /orgs/teams/{id}` | org member | Team + member list |
| `PATCH /orgs/teams/{id}` | creator/org admin | Rename |
| `DELETE /orgs/teams/{id}` | creator/org admin | Delete (grants to it cascade via service — delete `acl_grants` rows) |
| `POST /orgs/teams/{id}/members` | creator/org admin | `{user_id}` — 409 if target not in the same org |
| `DELETE /orgs/teams/{id}/members/{user_id}` | creator/org admin (or self — leaving) | Remove |

### Grants — new `app/domains/acl/` (service + schemas); routes mounted per resource so they read naturally

| Route | Who | Behaviour |
|---|---|---|
| `GET /{kbs\|assets\|harnesses}/{id}/grants` | owner | List grants with resolved principal names |
| `POST .../grants` | owner | `{principal_type, principal, permission}` — `principal` is a handle for users, a team id for teams. 404 unknown principal, 409 duplicate (PATCH-like upsert on permission change is fine too — decide in implementation, document in OpenAPI) |
| `DELETE .../grants/{grant_id}` | owner | Revoke |

`UserOut` additionally gains **`org_name`** (resolved from the relationship) — needed
by the explore tab header and finally lets the KC-063 tooltips say
"Team — visible to *\<org name\>*" as `docs/09` §7 intended.

### Org-scoped explore (OQ-20)

- `GET /v1/kbs/org` (auth, 404-equivalent empty for org-less): team-visible KBs
  owned by org members, `PublicKBOut` shape, `selectinload(owner)`.
- Assets/harnesses: **no new endpoints** — the existing `?visibility=team` filter
  already returns "mine + my org's team items" (KC-062 filter branches).
- Additionally, `KnowledgeBaseService.list_for_user` (dashboard) grows a union
  with granted KBs so a grantee can find what was shared with them (assets and
  harnesses get this for free — their list endpoints run through `base_predicate`).

## 6. Read/write-path changes

Extend `app/domains/organisations/predicates.py` (the helper stays the single
source of truth; no call site hand-rolls grant subqueries):

```python
def grant_subquery(resource_type, user, permissions=("viewer", "editor")) -> Select:
    """resource_ids of `resource_type` granted to the user directly or via a team."""
    my_teams = select(TeamMembership.team_id).where(TeamMembership.user_id == user.id)
    return select(AclGrant.resource_id).where(
        AclGrant.resource_type == resource_type,
        AclGrant.permission.in_(permissions),
        or_(
            and_(AclGrant.principal_type == "user", AclGrant.principal_id == user.id),
            and_(AclGrant.principal_type == "team", AclGrant.principal_id.in_(my_teams)),
        ),
    )

def readable_clause(model, resource_type, user) -> ColumnElement:
    """team_or_public_clause OR an ACL grant. Supersedes bare team_or_public_clause
    at the seven read sites."""
    return or_(team_or_public_clause(model, user),
               model.id.in_(grant_subquery(resource_type, user)))

def editable_clause(model, resource_type, user) -> ColumnElement:
    """Owner OR an editor grant."""
    return or_(model.owner_user_id == user.id,
               model.id.in_(grant_subquery(resource_type, user, permissions=("editor",))))
```

Rewire the seven `team_or_public_clause` call sites to `readable_clause` with
their resource type (`knowledge_base/service.py:93` → `"kb"`,
`learning/service.py:110` → `"kb"`, `assets/service.py:83,108` → `"asset"`,
`harnesses/service.py:36,56,148` → `"harness"`). The two `?visibility=` filter
branches narrow the base predicate and need no change. The learning chain
(`get_readable_path`, attempts, notes, learned) and the KB chain (sources,
search, Q&A, source-status poll) inherit grants transitively — that is the point
of OQ-17.

Write sites: add `get_editable_by_id` beside each domain's owner-guard method and
switch exactly the OQ-18 endpoints to it (KB add-URL/upload; asset add-version;
harness add-slot/swap-slot/submit-eval). `get_eval_run`/run-listing/SSE relax from
owner-only to editable so an editor can watch the run they submitted. Everything
else keeps the owner guard.

## 7. Frontend (MVP)

- **/org page**: "Teams" section under the member list — team list with member
  counts; create form; team detail expansion with member add (dropdown of org
  members, reusing the member-row pattern) and remove; rename/delete for managers.
  Replaces nothing; native `confirm()` is fine to match the page's existing style.
- **Share dialog** on KB workspace, asset detail, and harness compose (owner-only
  button next to the visibility badge): grant list + add form (user-by-handle or
  team picker, viewer/editor select) + revoke. One shared component
  (`components/ShareDialog.vue`), modeled on the compose-page modal pattern.
- **Explore**: fifth tab "My organisation" (`<ClientOnly>`, rendered only when
  `auth.user?.org_id`), three sections — KBs (`/api/kbs/org`, new BFF file, `kbs/`
  has no catch-all), Assets (`/api/assets?visibility=team`), Harnesses
  (`/api/harnesses?visibility=team`). Add `?tab=` URL sync to `switchTab` while
  in there (deep-linkable tabs, long-standing gap).
- Team tooltips upgrade to "Team — visible to <org name>" via `UserOut.org_name`.

## 8. Non-goals (this sprint)

- JWT claims of any kind (OQ-13 — decided, not deferred)
- Grantable `owner` permission, ownership transfer
- Team-level roles (team lead etc.) and nested teams
- Grants on boards (OQ-11), learning paths (covered via KB), or sources (OQ-12 dormant)
- A "shared with me" dashboard section beyond the KB list union (assets/harnesses
  already surface grants in their lists)
- User search/autocomplete endpoint — grants take exact handles
- Notification on grant ("X shared a KB with you") — needs the notification layer

## 9. Verification plan (live, three users)

Users: A (org X admin, owner of everything), B (org X member), C (**other-org or
org-less** — register fresh).

1. Teams: A creates team T, adds B. Adding C is refused (409, not same org).
   B (non-manager) cannot add/remove members (403); B can leave T (self-remove).
2. Team viewer grant: A grants T `viewer` on a **private** KB → B: KB 200 +
   sources + search + Q&A + shared learning path attempt/note/learned; C: 404.
   The KB appears in B's dashboard list.
3. Direct user grant, cross-org: A grants C `viewer` on a private asset by handle
   → C reads it and sees it in their asset list; C still 404s the KB.
4. Editor: A upgrades T's KB grant to `editor` → B adds a URL source (202) and
   the ingest completes; B commits an asset version on a granted asset; B
   add/swaps a harness slot and submits an eval, watching the SSE stream. C
   (viewer) gets 403/404 on all writes.
5. Revocation immediacy (unchanged tokens): A revokes the KB grant → B 404s
   instantly. A re-grants; A removes B from T → B 404s instantly (team-derived).
   Direct user grant to C survives C leaving/joining orgs.
6. Org leave cascade: B leaves org X → B's `team_memberships` rows are gone,
   team-grant access gone; B rejoins via invite, is *not* auto-restored to T.
7. Explore: B sees A's team-visible KB/assets/harnesses under "My organisation";
   C sees no such tab (org-less) or only their own org's items; `?tab=kbs` deep
   link lands on the right tab. Logged-out explore unchanged.
8. Regression: pytest suite green (115 + new), `vue-tsc` clean, public listings
   and v0.6.0 org flows unaffected.

## 10. Proposed ticket breakdown (v0.7.0)

| Ticket | Scope |
|---|---|
| KC-065 | Migration 014 + `Team`/`TeamMembership`/`AclGrant` models + registration + org-leave/remove membership cascade in `OrganisationService` |
| KC-066 | Teams API: service methods + `/orgs/teams` routes + schemas; unit tests for the manage/same-org/duplicate guards |
| KC-067 | ACL layer: `grant_subquery`/`readable_clause`/`editable_clause` in predicates.py + rewire 7 read sites + `get_editable_by_id` on the OQ-18 write sites + grants CRUD routes + `list_for_user` union + eval-run read relaxation; SQL-shape + guard unit tests |
| KC-068 | Org explore: `GET /v1/kbs/org` + `UserOut.org_name` + explore "My organisation" tab + `?tab=` URL sync + BFF (`kbs/org.get.ts`) |
| KC-069 | Frontend sharing: teams section on `/org` + `ShareDialog` on KB/asset/harness pages + org-name tooltips |
| KC-070 | Live verification (§9 script), docs sync (05 reality note, PROJECT_STATUS, CHANGELOG), release v0.7.0 |
