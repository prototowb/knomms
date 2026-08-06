import json, urllib.request, urllib.error

BASE = "http://localhost/api"
results = []

def call(method, path, token=None, body=None, expect=None):
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
    print(("✓" if ok else "✗"), name, ("— " + str(detail)[:120] if detail and not ok else ""))

def login(email, pw):
    s, d = call("POST", "/auth/login", body={"email": email, "password": pw})
    assert s == 200, (s, d)
    return d["access_token"]

dev = login("dev@localhost.dev", "devdev99")
tester = login("test@example.com", "password123")

KB = "0046f936-530e-43a9-9dab-676b62d78f44"
PATH = "bc42fe6c-12f2-4048-a44f-1ce0b396cdde"

# Setup: KB → team visibility, path → published (idempotent)
s, _ = call("PATCH", f"/v1/kbs/{KB}", dev, {"visibility": "team"})
check("setup: study KB → team", s == 200, s)
s, _ = call("POST", f"/learning-paths/{PATH}/publish", dev)
check("setup: path published", s == 200, s)

# 1. Same-org reader sees the path
s, path = call("GET", f"/learning-paths/{PATH}", tester)
check("reader (same org) GET path 200", s == 200, s)
concepts = [c for c in path["concepts"] if c["status"] != "pruned"]
with_item = next(c for c in concepts if c["assessment_items"])
item = with_item["assessment_items"][0]
check("answer key hidden from reader", item["correct_answer"] is None and item["distractors"] == [])

# 2. Wrong attempt (a non-correct choice) → persisted + feedback path
choices = item.get("choices") or []
s, wrong_res = call("POST", f"/learning-paths/{PATH}/concepts/{with_item['id']}/items/{item['id']}/attempt",
                    tester, {"answer": choices[0]["text"] if choices else "definitely wrong answer"})
if wrong_res and wrong_res.get("correct"):
    # first choice happened to be right — submit a definitely-wrong one
    s, wrong_res = call("POST", f"/learning-paths/{PATH}/concepts/{with_item['id']}/items/{item['id']}/attempt",
                        tester, {"answer": "definitely wrong answer"})
check("wrong attempt graded", s == 200 and wrong_res["correct"] is False, (s, wrong_res))
check("wrong attempt returns correct_answer", bool(wrong_res.get("correct_answer")))

# 3. Correct attempt using the revealed answer
s, right_res = call("POST", f"/learning-paths/{PATH}/concepts/{with_item['id']}/items/{item['id']}/attempt",
                    tester, {"answer": wrong_res["correct_answer"]})
check("correct attempt graded", s == 200 and right_res["correct"] is True, (s, right_res))

# 4. Cross-path scoping fix: grade the same item via a bogus concept pairing
other_concept = next((c for c in concepts if c["id"] != with_item["id"]), None)
if other_concept:
    s, _ = call("POST", f"/learning-paths/{PATH}/concepts/{other_concept['id']}/items/{item['id']}/attempt",
                tester, {"answer": "x"})
    check("item under wrong concept → 404", s == 404, s)

# 5. Mark learned
s, _ = call("POST", f"/learning-paths/{PATH}/concepts/{with_item['id']}/learned", tester)
check("reader marks concept learned", s in (200, 201), s)

# 6. Passage-anchored thread
passage = (with_item.get("source_passages") or [{}])[0]
s, thread = call("POST", f"/learning-paths/{PATH}/concepts/{with_item['id']}/threads", tester,
                 {"title": "Why is this the right answer?", "body": "Confused by the passage.",
                  "passage_chunk_id": passage.get("chunk_id")})
check("reader creates anchored thread", s in (200, 201) and bool(thread.get("id")), (s, thread))
check("excerpt snapshotted", bool(thread.get("passage_excerpt")), thread.get("passage_excerpt"))

s, bad = call("POST", f"/learning-paths/{PATH}/concepts/{with_item['id']}/threads", tester,
              {"title": "bad anchor", "passage_chunk_id": "00000000-0000-0000-0000-000000000000"})
check("foreign anchor → 422", s == 422, s)

# 7. Owner replies; reader sees the reply
s, post = call("POST", f"/learning-paths/{PATH}/threads/{thread['id']}/posts", dev, {"body": "Because the eval run report says so — see the excerpt."})
check("owner replies", s in (200, 201), s)
s, tview = call("GET", f"/learning-paths/{PATH}/threads/{thread['id']}", tester)
check("reader sees reply (posts ASC)", s == 200 and len(tview["posts"]) == 1 and tview["posts"][0]["author"]["handle"] == "dev", (s, tview))

# 8. Delete rules: reader cannot delete owner's post; owner can
s, _ = call("DELETE", f"/learning-paths/{PATH}/threads/{thread['id']}/posts/{post['id']}", tester)
check("reader cannot delete owner's post (403)", s == 403, s)
s, reply2 = call("POST", f"/learning-paths/{PATH}/threads/{thread['id']}/posts", tester, {"body": "thanks!"})
s, _ = call("DELETE", f"/learning-paths/{PATH}/threads/{thread['id']}/posts/{reply2['id']}", dev)
check("path owner moderates reader post (204)", s == 204, s)

# 9. Analytics: owner sees tester; non-owner 404
s, an = call("GET", f"/learning-paths/{PATH}/analytics", dev)
tester_row = next((l for l in an["learners"] if l["user"]["handle"] == "tester"), None) if s == 200 else None
check("owner analytics 200 + tester row", s == 200 and tester_row is not None, (s, an if s != 200 else ""))
if tester_row:
    check("tester attempts counted", tester_row["attempt_count"] >= 2, tester_row)
    check("tester learned counted", tester_row["learned_count"] >= 1, tester_row)
    cstats = next((c for c in an["concepts"] if c["concept_id"] == with_item["id"]), None)
    check("concept has wrong-answer aggregation", cstats is not None and cstats["attempt_count"] >= 2, cstats)
s, _ = call("GET", f"/learning-paths/{PATH}/analytics", tester)
check("reader analytics → 404", s == 404, s)

# 10. Org-less outsider: register fresh, everything 404
import time
email = f"outsider-{int(time.time())}@example.com"
s, _ = call("POST", "/auth/register", body={"email": email, "password": "password123", "handle": f"out{int(time.time())}", "display_name": "Outsider"})
outsider = login(email, "password123")
s, _ = call("GET", f"/learning-paths/{PATH}", outsider)
check("org-less outsider GET path → 404", s == 404, s)
s, _ = call("GET", f"/learning-paths/{PATH}/concepts/{with_item['id']}/threads", outsider)
check("org-less outsider threads → 404", s == 404, s)
s, _ = call("POST", f"/learning-paths/{PATH}/concepts/{with_item['id']}/items/{item['id']}/attempt", outsider, {"answer": "x"})
check("org-less outsider attempt → 404", s == 404, s)

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} checks passed")
raise SystemExit(1 if fails else 0)
