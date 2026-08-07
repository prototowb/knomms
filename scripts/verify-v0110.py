"""Live verification for v0.11.0 — mastery gates (docs/14 §8).

Two users, same org: dev (path owner) + tester (learner). Runs against the
Colima stack via the BFF chain. Robust to attempt history left by earlier
verification runs — expectations are computed from the payload's own gate
fields, not from assumed history. Leaves the path with gates off.
"""

import json, urllib.request, urllib.error

BASE = "http://localhost/api"
results = []

def call(method, path, token=None, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token: req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        try: payload = json.loads(e.read() or b"null")
        except Exception: payload = None
        return e.code, payload

def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("✓" if ok else "✗"), name, ("— " + str(detail)[:140] if detail and not ok else ""))

def login(email, pw):
    s, d = call("POST", "/auth/login", body={"email": email, "password": pw})
    assert s == 200, (s, d)
    return d["access_token"]

dev = login("dev@localhost.dev", "devdev99")
tester = login("test@example.com", "password123")

KB = "0046f936-530e-43a9-9dab-676b62d78f44"
PATH = "bc42fe6c-12f2-4048-a44f-1ce0b396cdde"

def get_path(token):
    s, p = call("GET", f"/learning-paths/{PATH}", token)
    assert s == 200, (s, p)
    return p

def active(p):
    return [c for c in p["concepts"] if c["status"] != "pruned"]

def master(concept):
    """Master one unlocked concept as tester: items via wrong→reveal→correct,
    item-less via learned mark."""
    items = concept["assessment_items"]
    if not items:
        s, _ = call("POST", f"/learning-paths/{PATH}/concepts/{concept['id']}/learned", tester)
        assert s in (200, 201), s
        return
    for item in items:
        url = f"/learning-paths/{PATH}/concepts/{concept['id']}/items/{item['id']}/attempt"
        s, res = call("POST", url, tester, {"answer": "___definitely wrong___"})
        assert s == 200, (s, res)
        if not res["correct"]:
            s, res = call("POST", url, tester, {"answer": res["correct_answer"]})
            assert s == 200 and res["correct"], (s, res)

# ── Setup (idempotent) ────────────────────────────────────────────────────────
s, _ = call("PATCH", f"/v1/kbs/{KB}", dev, {"visibility": "team"})
check("setup: KB team-visible", s == 200, s)
s, _ = call("POST", f"/learning-paths/{PATH}/publish", dev)
check("setup: path published", s == 200, s)

# ── 1. PATCH validation + authz ───────────────────────────────────────────────
s, _ = call("PATCH", f"/learning-paths/{PATH}", dev, {"mastery_mode": "brutal"})
check("bad mastery_mode → 422", s == 422, s)
s, _ = call("PATCH", f"/learning-paths/{PATH}", dev, {"mastery_threshold": 1.5})
check("threshold > 1 → 422", s == 422, s)
s, _ = call("PATCH", f"/learning-paths/{PATH}", dev, {"mastery_threshold": 0})
check("threshold 0 → 422", s == 422, s)
s, _ = call("PATCH", f"/learning-paths/{PATH}", tester, {"mastery_mode": "off"})
check("non-owner PATCH → 404", s == 404, s)

s, p = call("PATCH", f"/learning-paths/{PATH}", dev, {"mastery_mode": "hard", "mastery_threshold": 1.0})
check("owner sets hard/1.0", s == 200 and p["mastery_mode"] == "hard" and p["mastery_threshold"] == 1.0, (s, p))

# ── 2. Owner exemption ────────────────────────────────────────────────────────
own = get_path(dev)
check("owner payload ungated (gate null, nothing locked, content present)",
      all(c["gate"] is None and not c["locked"] and c["explanation_text"] for c in active(own)))

# ── 3. Learner gate state: internal consistency + redaction ──────────────────
lp = get_path(tester)
acts = active(lp)
check("every non-pruned concept has gate state", all(c["gate"] is not None for c in acts))

blocked = False
consistent = True
for c in acts:
    if c["locked"] != blocked: consistent = False
    blocked = blocked or not c["gate"]["mastered"]
check("locked flags consistent with mastered sequence", consistent,
      [(c["title"], c["locked"], c["gate"]) for c in acts])

locked = [c for c in acts if c["locked"]]
check("hard/1.0 leaves at least one concept locked for tester", len(locked) > 0)

if locked:
    L = locked[0]
    check("locked concept redacted",
          L["explanation_text"] == "" and L["assessment_items"] == []
          and L["source_passages"] == [] and L["instructor_annotation"] is None, L)
    check("locked concept keeps title/position for nav", bool(L["title"]))

    # ── 4. Hard-mode 422 guards ───────────────────────────────────────────────
    s, d = call("POST", f"/learning-paths/{PATH}/concepts/{L['id']}/items/00000000-0000-0000-0000-000000000000/attempt", tester, {"answer": "x"})
    check("attempt on locked concept → 422", s == 422, (s, d))
    s, _ = call("POST", f"/learning-paths/{PATH}/concepts/{L['id']}/learned", tester)
    check("mark-learned on locked concept → 422", s == 422, s)
    s, _ = call("GET", f"/learning-paths/{PATH}/concepts/{L['id']}/threads", tester)
    check("thread list on locked concept → 422", s == 422, s)
    s, _ = call("POST", f"/learning-paths/{PATH}/concepts/{L['id']}/threads", tester, {"title": "hi"})
    check("thread create on locked concept → 422", s == 422, s)

    # ── 5. Mastering predecessors unlocks ─────────────────────────────────────
    for c in acts:
        if c["id"] == L["id"]: break
        if not c["gate"]["mastered"]:
            master(c)
    lp2 = get_path(tester)
    L2 = next(c for c in active(lp2) if c["id"] == L["id"])
    check("locked concept unlocks after mastering predecessors",
          not L2["locked"] and L2["explanation_text"] != "", L2["locked"])
    if L2["assessment_items"]:
        s, res = call("POST", f"/learning-paths/{PATH}/concepts/{L2['id']}/items/{L2['assessment_items'][0]['id']}/attempt",
                      tester, {"answer": "___definitely wrong___"})
        check("attempt on unlocked concept works, response shape unchanged",
              s == 200 and set(res) == {"correct", "correct_answer", "grounding_passage_id", "feedback"}, (s, res))

# ── 6. Soft mode: warns, never blocks or redacts ──────────────────────────────
s, _ = call("PATCH", f"/learning-paths/{PATH}", dev, {"mastery_mode": "soft"})
check("owner sets soft", s == 200, s)
lp3 = get_path(tester)
soft_locked = [c for c in active(lp3) if c["locked"]]
check("soft mode still reports locked concepts", len(soft_locked) > 0,
      "tester mastered everything — soft-lock content check skipped")
if soft_locked:
    S = soft_locked[0]
    check("soft-locked concept NOT redacted", S["explanation_text"] != "" and S["gate"] is not None, S)
    s, _ = call("GET", f"/learning-paths/{PATH}/concepts/{S['id']}/threads", tester)
    check("thread list on soft-locked concept → 200", s == 200, s)
    if S["assessment_items"]:
        s, res = call("POST", f"/learning-paths/{PATH}/concepts/{S['id']}/items/{S['assessment_items'][0]['id']}/attempt",
                      tester, {"answer": "___definitely wrong___"})
        check("attempt on soft-locked concept → 200", s == 200, (s, res))

# ── 7. Off: byte-identical default ────────────────────────────────────────────
s, _ = call("PATCH", f"/learning-paths/{PATH}", dev, {"mastery_mode": "off"})
check("owner sets off", s == 200, s)
lp4 = get_path(tester)
check("off mode: gate null, nothing locked, content present",
      all(c["gate"] is None and not c["locked"] and c["explanation_text"] for c in active(lp4)))

# ── 8. learner_count + mastery_mode on summaries ─────────────────────────────
s, paths = call("GET", f"/kb/{KB}/learning-paths", tester)
row = next((r for r in paths if r["id"] == PATH), None) if s == 200 else None
check("path list has our path", row is not None, (s, paths))
if row:
    check("learner_count ≥ 1 (tester active)", row["learner_count"] >= 1, row)
    check("summary carries mastery_mode", row["mastery_mode"] == "off", row)

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} checks passed")
raise SystemExit(1 if fails else 0)
