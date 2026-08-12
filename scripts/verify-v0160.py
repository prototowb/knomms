"""Live verification for v0.16.0 — prerequisite graph (docs/19 §7).

Two layers:
1. Inference: regenerate a path on the multi-source KB — the `prerequisites`
   field exists everywhere; IF the model proposed edges, they are shape-valid,
   sibling-scoped, and cycle-free (edge presence itself is model-dependent
   and not asserted).
2. Gating (deterministic): stamp a known edge set onto the standing
   multi-concept path via SQL (no edit API yet — part 2), then assert the
   graph rules through the learner API: dependents lock on unmastered
   required prereqs, edge-less concepts stay open (the sequence rule would
   have locked them), chips data ships, and the edge-less regression path
   still gates linearly.

Run from the repo root with DOCKER_HOST exported (SQL goes through
`docker compose exec db psql`).
"""

import json, subprocess, time, urllib.request, urllib.error

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


def sql(statement: str) -> None:
    subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "psql", "-U", "kc", "-d", "knomms",
         "-v", "ON_ERROR_STOP=1", "-c", statement],
        check=True, capture_output=True,
    )


dev = login("dev@localhost.dev", "devdev99")
tester = login("test@example.com", "password123")

# ── 1. Inference pass on a freshly generated path ─────────────────────────────
s, kbs = call("GET", "/kbs", dev)
KB = None
for kb in kbs:
    s, srcs = call("GET", f"/kb/{kb['id']}/sources", dev)
    if s == 200 and sum(1 for x in srcs if x["ingestion_status"] == "embedded") >= 2:
        KB = kb["id"]
        break
check("setup: multi-source KB found", KB is not None)

s, newpath = call("POST", f"/v1/kbs/{KB}/learning-paths", dev,
                  {"learning_goal": "Prerequisite graph verification"})
check("path generation accepted (202)", s == 202, (s, newpath))
pstatus = "generating"
deadline = time.time() + 900
while time.time() < deadline and pstatus == "generating":
    time.sleep(10)
    s, p = call("GET", f"/learning-paths/{newpath['id']}", dev)
    pstatus = p.get("status") if s == 200 else pstatus
check("generation completed (draft)", pstatus == "draft", pstatus)

if pstatus == "draft":
    check("every concept carries a prerequisites list",
          all(isinstance(c.get("prerequisites"), list) for c in p["concepts"]))
    ids = {c["id"] for c in p["concepts"]}
    all_edges = [(c["id"], e) for c in p["concepts"] for e in c["prerequisites"]]
    print(f"  [inference proposed {len(all_edges)} edge(s) across {len(ids)} concepts]", flush=True)
    if all_edges:
        check("edges are sibling-scoped with valid shape", all(
            e["concept_id"] in ids and e["concept_id"] != cid
            and e["strength"] in ("required", "recommended")
            for cid, e in all_edges), all_edges)
        # cycle check over required+recommended edges
        adj = {}
        for cid, e in all_edges:
            adj.setdefault(e["concept_id"], set()).add(cid)
        def cyclic():
            seen, stack = set(), set()
            def dfs(n):
                seen.add(n); stack.add(n)
                for m in adj.get(n, ()):
                    if m in stack or (m not in seen and dfs(m)):
                        return True
                stack.discard(n)
                return False
            return any(dfs(n) for n in list(adj) if n not in seen)
        check("edge set is acyclic", not cyclic())

# ── 2. Deterministic graph gating on the standing cohort path ─────────────────
PATH = "bc42fe6c-12f2-4048-a44f-1ce0b396cdde"
s, _ = call("POST", f"/learning-paths/{PATH}/publish", dev)
s, full = call("GET", f"/learning-paths/{PATH}", dev)
active = [c for c in full["concepts"] if c["status"] != "pruned"]
check("standing path has ≥3 non-pruned concepts", len(active) >= 3, len(active))
c0, c1 = active[0], active[1]

# Stamp: c1 requires c0; every other concept edge-less
sql(f"UPDATE path_concepts SET prerequisites = '[]'::jsonb WHERE path_id = '{PATH}'")
edge = json.dumps([{"concept_id": c0["id"], "strength": "required", "rationale": "verification edge"}])
sql(f"UPDATE path_concepts SET prerequisites = '{edge}'::jsonb WHERE id = '{c1['id']}'")

s, _ = call("PATCH", f"/learning-paths/{PATH}", dev, {"mastery_mode": "hard", "mastery_threshold": 1.0})
check("hard gates set", s == 200, s)

s, lp = call("GET", f"/learning-paths/{PATH}", tester)
gact = [c for c in lp["concepts"] if c["status"] != "pruned"]
by_id = {c["id"]: c for c in gact}
g0, g1 = by_id[c0["id"]], by_id[c1["id"]]
independents = [c for c in gact if c["id"] not in (c0["id"], c1["id"])]

check("chips data ships to the learner", g1["prerequisites"][0]["concept_id"] == c0["id"], g1["prerequisites"])
check("graph mode: independent concepts all unlocked", all(not c["locked"] for c in independents),
      [(c["title"], c["locked"]) for c in independents])
expected_locked = not g0["gate"]["mastered"]
check("dependent locked iff required prereq unmastered", g1["locked"] == expected_locked,
      (g1["locked"], g0["gate"]))

if expected_locked and g0["gate"]["item_count"] == 0:
    # master c0 via learned-mark, then the dependent must unlock
    s, _ = call("POST", f"/learning-paths/{PATH}/concepts/{c0['id']}/learned", tester)
    s, lp2 = call("GET", f"/learning-paths/{PATH}", tester)
    g1b = next(c for c in lp2["concepts"] if c["id"] == c1["id"])
    check("mastering the prereq unlocks the dependent", not g1b["locked"], g1b["locked"])
elif expected_locked:
    # master c0 by answering its items (wrong→reveal→correct)
    for item in g0["assessment_items"]:
        url = f"/learning-paths/{PATH}/concepts/{c0['id']}/items/{item['id']}/attempt"
        s, res = call("POST", url, tester, {"answer": "___wrong___"})
        if s == 200 and not res["correct"]:
            call("POST", url, tester, {"answer": res["correct_answer"]})
    s, lp2 = call("GET", f"/learning-paths/{PATH}", tester)
    g1b = next(c for c in lp2["concepts"] if c["id"] == c1["id"])
    check("mastering the prereq unlocks the dependent", not g1b["locked"], g1b["locked"])
else:
    check("mastering the prereq unlocks the dependent", not g1["locked"], "prereq already mastered")

# ── 3. Regression: edge-less path keeps the sequence rule ─────────────────────
sql(f"UPDATE path_concepts SET prerequisites = '[]'::jsonb WHERE path_id = '{PATH}'")
s, lp3 = call("GET", f"/learning-paths/{PATH}", tester)
seq = [c for c in lp3["concepts"] if c["status"] != "pruned"]
blocked, consistent = False, True
for c in seq:
    if c["locked"] != blocked: consistent = False
    blocked = blocked or not c["gate"]["mastered"]
check("edge-less path gates by sequence (v0.11.0 rule)", consistent,
      [(c["title"], c["locked"], c["gate"]["mastered"]) for c in seq])

# cleanup: gates off
call("PATCH", f"/learning-paths/{PATH}", dev, {"mastery_mode": "off"})

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} checks passed")
raise SystemExit(1 if fails else 0)
