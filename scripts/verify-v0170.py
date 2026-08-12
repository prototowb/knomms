"""Live verification for v0.17.0 — polish wave (docs/20).

Three feature areas, one script: instructor prerequisite editing (OQ-88),
discussion post editing (OQ-89), study-KB rebuild (OQ-90). Plus the
v0.16.0 gate regression. Run from the repo root.
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

PATH = "bc42fe6c-12f2-4048-a44f-1ce0b396cdde"
call("POST", f"/learning-paths/{PATH}/publish", dev)
s, full = call("GET", f"/learning-paths/{PATH}", dev)
active = [c for c in full["concepts"] if c["status"] != "pruned"]
check("setup: standing path with ≥3 concepts", len(active) >= 3, len(active))
c0, c1, c2 = active[0], active[1], active[2]

# ── 1. Prerequisite editing (OQ-88) ───────────────────────────────────────────
edge = [{"concept_id": c0["id"], "strength": "required", "rationale": "verify edit"}]
s, upd = call("PATCH", f"/learning-paths/{PATH}/concepts/{c1['id']}", dev, {"prerequisites": edge})
check("owner sets prerequisites via PATCH", s == 200 and upd["prerequisites"][0]["concept_id"] == c0["id"], (s, upd))

s, _ = call("PATCH", f"/learning-paths/{PATH}/concepts/{c1['id']}", dev,
            {"prerequisites": [{"concept_id": c1["id"], "strength": "required", "rationale": ""}]})
check("self-edge → 422", s == 422, s)
s, _ = call("PATCH", f"/learning-paths/{PATH}/concepts/{c1['id']}", dev,
            {"prerequisites": [{"concept_id": "00000000-0000-0000-0000-000000000000", "strength": "required", "rationale": ""}]})
check("non-sibling → 422", s == 422, s)
# cycle: c1 requires c0 (set above); now try c0 requires c1
s, _ = call("PATCH", f"/learning-paths/{PATH}/concepts/{c0['id']}", dev,
            {"prerequisites": [{"concept_id": c1["id"], "strength": "required", "rationale": ""}]})
check("cycle-closing edit → 422", s == 422, s)
s, _ = call("PATCH", f"/learning-paths/{PATH}/concepts/{c1['id']}", tester, {"prerequisites": edge})
check("non-owner prerequisite edit → 404", s == 404, s)

# gates respect the edited edge
s, _ = call("PATCH", f"/learning-paths/{PATH}", dev, {"mastery_mode": "hard", "mastery_threshold": 1.0})
s, lp = call("GET", f"/learning-paths/{PATH}", tester)
by_id = {c["id"]: c for c in lp["concepts"]}
expected = not by_id[c0["id"]]["gate"]["mastered"]
check("edited edge drives the gate", by_id[c1["id"]]["locked"] == expected,
      (by_id[c1["id"]]["locked"], by_id[c0["id"]]["gate"]))
check("concepts without edges stay open", not by_id[c2["id"]]["locked"], by_id[c2["id"]]["locked"])

# clear edges + gates off (cleanup for later sections)
call("PATCH", f"/learning-paths/{PATH}/concepts/{c1['id']}", dev, {"prerequisites": []})
call("PATCH", f"/learning-paths/{PATH}", dev, {"mastery_mode": "off"})

# ── 2. Post editing (OQ-89) ───────────────────────────────────────────────────
s, thread = call("POST", f"/learning-paths/{PATH}/concepts/{c0['id']}/threads", tester,
                 {"title": "Edit verification thread", "body": "original thread body"})
check("thread created", s in (200, 201), (s, thread))  # BFF proxies respond 200
s, post = call("POST", f"/learning-paths/{PATH}/threads/{thread['id']}/posts", tester,
               {"body": "original post body"})
check("post created", s in (200, 201), (s, post))

s, edited = call("PATCH", f"/learning-paths/{PATH}/threads/{thread['id']}/posts/{post['id']}",
                 tester, {"body": "edited post body"})
check("author edits own post", s == 200 and edited["body"] == "edited post body"
      and edited.get("edited_at"), (s, edited))
s, _ = call("PATCH", f"/learning-paths/{PATH}/threads/{thread['id']}/posts/{post['id']}",
            dev, {"body": "owner rewrite attempt"})
check("path owner cannot rewrite (403 — moderate by delete)", s == 403, s)
s, _ = call("PATCH", f"/learning-paths/{PATH}/threads/{thread['id']}/posts/{post['id']}",
            tester, {"body": "   "})
check("empty edit → 422", s == 422, s)
s, tview = call("GET", f"/learning-paths/{PATH}/threads/{thread['id']}", dev)
check("edited body + edited_at visible to readers", s == 200 and any(
    p["body"] == "edited post body" and p.get("edited_at") for p in tview["posts"]), (s, tview))

# ── 3. Study-KB rebuild (OQ-90) ───────────────────────────────────────────────
s, harnesses = call("GET", "/v1/harnesses", dev)
H = next((h["id"] for h in (harnesses or []) if h.get("study_kb_id")), None)
if H is None:
    # No standing study KB — create one on the first harness with anything to study
    for h in harnesses or []:
        s, created = call("POST", f"/v1/harnesses/{h['id']}/study-kb", dev, {})
        if s == 200 and created.get("projected", 0) > 0:
            H = h["id"]
            # wait for the initial projection to embed before rebuild checks
            deadline = time.time() + 300
            while time.time() < deadline:
                s, st = call("GET", f"/v1/harnesses/{H}/study-kb", dev)
                if s == 200 and all(d["ingestion_status"] == "embedded" for d in st["docs"]):
                    break
                time.sleep(5)
            break
check("setup: harness with study KB (found or created)", H is not None,
      [h.get("title") for h in (harnesses or [])])
if H:
    s, before = call("GET", f"/v1/harnesses/{H}/study-kb", dev)
    before_ids = {d["source_id"] for d in before["docs"]}
    s, refresh = call("POST", f"/v1/harnesses/{H}/study-kb", dev, {})
    check("plain refresh stays idempotent", s == 200 and refresh["projected"] == 0
          and refresh["skipped"] == len(before_ids), (s, refresh))
    s, rebuilt = call("POST", f"/v1/harnesses/{H}/study-kb", dev, {"rebuild": True})
    check("rebuild re-projects everything", s == 200 and rebuilt["projected"] == len(before_ids)
          and rebuilt["skipped"] == 0, (s, rebuilt))
    s, after = call("GET", f"/v1/harnesses/{H}/study-kb", dev)
    after_ids = {d["source_id"] for d in after["docs"]}
    check("rebuild used fresh Source ids", len(after_ids) == len(before_ids)
          and not (after_ids & before_ids), (len(before_ids), len(after_ids & before_ids)))
    deadline = time.time() + 300
    done = False
    while time.time() < deadline:
        s, st = call("GET", f"/v1/harnesses/{H}/study-kb", dev)
        if s == 200 and all(d.get("ingestion_status") == "embedded" for d in st["docs"]):
            done = True
            break
        time.sleep(5)
    check("rebuilt docs re-embedded", done)
    s, refresh2 = call("POST", f"/v1/harnesses/{H}/study-kb", dev, {})
    check("refresh idempotent again after rebuild", s == 200 and refresh2["projected"] == 0, (s, refresh2))

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} checks passed")
raise SystemExit(1 if fails else 0)
