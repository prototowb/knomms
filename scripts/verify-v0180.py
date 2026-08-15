"""Live verification for v0.18.0 — editor-authored learning paths (docs/22).

Three users: dev (KB owner), tester (editor grantee — authors a path and
keeps its bundle), a fresh viewer grantee (sees but cannot author). Plus
the board team-visibility 422s. Editor path generation takes ~5 min on CPU.
"""

import json, time, urllib.request, urllib.error

BASE = "http://localhost/api"
results = []


def call(method, path, token=None, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token: req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        try: payload = json.loads(e.read() or b"null")
        except Exception: payload = None
        return e.code, payload


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("✓" if ok else "✗"), name, ("— " + str(detail)[:140] if detail and not ok else ""), flush=True)


def login(email, pw):
    s, d = call("POST", "/auth/login", body={"email": email, "password": pw})
    assert s == 200, (s, d)
    return d["access_token"]


dev = login("dev@localhost.dev", "devdev99")
tester = login("test@example.com", "password123")

stamp = int(time.time())
call("POST", "/auth/register", body={"email": f"viewer-{stamp}@example.com", "password": "password123",
                                     "handle": f"viewer{stamp}", "display_name": "Viewer"})
viewer = login(f"viewer-{stamp}@example.com", "password123")

# ── Setup: dev-owned multi-source KB; tester=editor, viewer=viewer ────────────
s, kbs = call("GET", "/kbs", dev)
KB = None
for kb in kbs:
    s, srcs = call("GET", f"/kb/{kb['id']}/sources", dev)
    if s == 200 and sum(1 for x in srcs if x["ingestion_status"] == "embedded") >= 2:
        KB = kb["id"]
        break
check("setup: dev KB with embedded sources", KB is not None)
call("PATCH", f"/v1/kbs/{KB}", dev, {"visibility": "private"})  # grants must carry access alone

s, g1 = call("POST", f"/v1/kbs/{KB}/grants", dev,
             {"principal_type": "user", "principal": "tester", "permission": "editor"})
check("editor grant to tester", s in (200, 201), (s, g1))
s, g2 = call("POST", f"/v1/kbs/{KB}/grants", dev,
             {"principal_type": "user", "principal": f"viewer{stamp}", "permission": "viewer"})
check("viewer grant to fresh user", s in (200, 201), (s, g2))

# ── 1. editable flag (OQ-93) ──────────────────────────────────────────────────
s, meta = call("GET", f"/v1/kbs/{KB}", dev)
check("owner sees editable=true", s == 200 and meta["editable"] is True, (s, meta))
s, meta = call("GET", f"/v1/kbs/{KB}", tester)
check("editor grantee sees editable=true", s == 200 and meta["editable"] is True, (s, meta))
s, meta = call("GET", f"/v1/kbs/{KB}", viewer)
check("viewer grantee sees editable=false", s == 200 and meta["editable"] is False, (s, meta))

# ── 2. authoring guard (OQ-92) ────────────────────────────────────────────────
s, _ = call("POST", f"/v1/kbs/{KB}/learning-paths", viewer, {"learning_goal": "viewer attempt"})
check("viewer create path → 404", s == 404, s)

s, newpath = call("POST", f"/v1/kbs/{KB}/learning-paths", tester,
                  {"learning_goal": "Editor-authored verification path"})
check("editor create path → 202", s == 202, (s, newpath))
PID = newpath["id"] if s == 202 else None

pstatus = "generating"
deadline = time.time() + 900
while PID and time.time() < deadline and pstatus == "generating":
    time.sleep(10)
    s, p = call("GET", f"/learning-paths/{PID}", tester)
    pstatus = p.get("status") if s == 200 else pstatus
check("editor path generated (draft)", pstatus == "draft", pstatus)

# ── 3. creator-owned bundle (OQ-92) ──────────────────────────────────────────
if PID:
    s, _ = call("POST", f"/learning-paths/{PID}/publish", tester)
    check("editor publishes their path", s == 200, s)
    s, _ = call("GET", f"/learning-paths/{PID}/analytics", tester)
    check("path creator reads analytics", s == 200, s)
    s, _ = call("GET", f"/learning-paths/{PID}/analytics", dev)
    check("KB owner gets 404 on foreign path analytics (creator-owned bundle)", s == 404, s)
    s, _ = call("PATCH", f"/learning-paths/{PID}", tester, {"mastery_mode": "soft"})
    check("path creator configures gates", s == 200, s)
    s, _ = call("PATCH", f"/learning-paths/{PID}", dev, {"mastery_mode": "hard"})
    check("KB owner cannot configure foreign path gates (404)", s == 404, s)
    s, p = call("GET", f"/learning-paths/{PID}", dev)
    check("KB owner reads the published path as a learner", s == 200 and p["status"] == "published", s)

# ── 4. board team-visibility 422 (OQ-94) ─────────────────────────────────────
s, board = call("POST", "/v1/boards", dev, {"title": f"vis-verify-{stamp}"})
BOARD = board["id"]
s, d = call("PATCH", f"/v1/boards/{BOARD}", dev, {"visibility": "team"})
check("board PATCH visibility=team → 422", s == 422 and "excluded by design" in str(d), (s, d))
s, _ = call("POST", "/v1/boards", dev, {"title": "x", "visibility": "team"})
check("board create visibility=team → 422", s == 422, s)
s, _ = call("PATCH", f"/v1/boards/{BOARD}", dev, {"visibility": "public"})
check("board private→public still works", s == 200, s)
s, _ = call("PATCH", f"/v1/boards/{BOARD}", dev, {"visibility": "private"})
check("board →private still works", s == 200, s)

# ── 5. Regression: revoke removes authoring ───────────────────────────────────
s, grants = call("GET", f"/v1/kbs/{KB}/grants", dev)
gid = next((g["id"] for g in grants if g.get("permission") == "editor"), None)
if gid:
    call("DELETE", f"/v1/kbs/{KB}/grants/{gid}", dev)
    s, _ = call("POST", f"/v1/kbs/{KB}/learning-paths", tester, {"learning_goal": "post-revoke"})
    check("revoked editor create → 404 (immediacy)", s == 404, s)
    s, meta = call("GET", f"/v1/kbs/{KB}", tester)
    check("revoked editor loses readable KB entirely (private)", s == 404, s)

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} checks passed")
raise SystemExit(1 if fails else 0)
