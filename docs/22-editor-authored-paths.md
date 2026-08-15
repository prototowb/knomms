# Editor-Authored Learning Paths — Closing Team Workspaces (Design)

> Status: **proposed** (2026-08-15). The audit (`docs/21-team-workspaces-audit.md`)
> found V2 #4 ~80% delivered with one blocking gap: an editor grantee can
> grow a KB's corpus but cannot invoke the curriculum agent over it —
> stopping the professional-team persona's own journey (spec §1.4 flows
> 1–2) at its second step. This sprint closes it, plus the audit's
> accept-then-ignore board-visibility inconsistency.
> Proposed sprint: **v0.18.0 = KC-116–118**.

## Design decisions

| # | Decision | Call | Rationale |
|---|---|---|---|
| OQ-92 | Who may author, and who owns the result | `create_stub` relaxes `get_by_id` → `get_editable_by_id` (owner or **editor** grant, the OQ-18 surface). The path creator keeps the standard owner bundle — publish, mastery gates, concept curation/prerequisites, analytics — because **every piece of the bundle is path-scoped**: `path_analytics` aggregates only that path's attempts/progress (OQ-39's classroom-teacher rationale applies to the path's own author; the KB owner's other cohorts are invisible to it), and disclosure reach is unchanged (a reader still needs published + readable-KB — an editor cannot widen the KB's audience by authoring). The audit's surveillance concern targeted a *shared* bundle; a creator-owned bundle doesn't have the problem | The alternative (KB owner co-owns every path) adds a second privileged party to publish/gates/analytics for no identified threat. KB-owner *moderation* of foreign paths (unpublish/delete) is deferred with the general absence of path deletion — nobody can delete a path today |
| OQ-93 | Editability surfaced to clients | `KnowledgeBaseOut.editable: bool` — computed for the requester on the single-KB GET (owner, or editor grant via `has_grant`). Frontend gates "＋ New path" and the add-source controls on `editable` instead of `isOwner` | KC-067 gave editors backend write access but the UI still hides add-URL/upload behind `isOwner` — editors have been writing blind via API only. One server-computed flag beats teaching the client grant semantics |
| OQ-94 | Board `visibility="team"` | **Reject with 422** ("Boards support private or public — team boards were excluded by design, see docs/21 §3.2") at PATCH; create/fork already default and the UI never offers it, but the service validates too | OQ-11 has been reaffirmed three times; implementing team board reads would silently reverse a standing decision. Today's accept-then-ignore is the worst state: write-accepted, read-dead |

## Verification plan (KC-118)

1. Unit: board-visibility validation; `editable` shaping (pure seam if available).
2. Live (three users): owner grants editor to B on a private KB → B's KB GET shows `editable: true`, B creates a learning path (202→draft), B publishes, B's analytics work for B's path and 404 for the owner (creator-owned bundle), owner's paths untouched; viewer grantee C gets `editable: false` and create → 404; board PATCH `visibility="team"` → 422; regression: owner authoring, existing paths, board private↔public sync.
3. Full pytest; vue-tsc.
