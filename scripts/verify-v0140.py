"""Live verification for v0.14.0 — synthesis persistence & board projection (docs/17 §7).

Fast checks (save/list/delete/guards) plus the projection path: saved
synthesis → board → `synthesis` Source embedded in the board's KB →
keyword search finds the answer text → idempotent re-add reuses the
Source. Ends with the enqueue-race regression: two rapid board URL adds
must both leave `pending`.
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


def wait_source(source_id, token, timeout=180):
    deadline = time.time() + timeout
    status = "?"
    while time.time() < deadline:
        s, src = call("GET", f"/v1/sources/{source_id}", token)
        status = src.get("ingestion_status") if s == 200 else f"http:{s}"
        if status in ("embedded", "failed"):
            return status
        time.sleep(4)
    return f"timeout:{status}"


dev = login("dev@localhost.dev", "devdev99")
tester = login("test@example.com", "password123")

# ── Setup: KB with ≥2 embedded sources (built by verify-v0120) ────────────────
s, kbs = call("GET", "/kbs", dev)
KB, embedded = None, []
for kb in kbs:
    s, srcs = call("GET", f"/kb/{kb['id']}/sources", dev)
    if s != 200: continue
    emb = [x for x in srcs if x["ingestion_status"] == "embedded"]
    if len(emb) >= 2:
        KB, embedded = kb["id"], emb
        break
check("setup: KB with ≥2 embedded sources", KB is not None)
if KB is None:
    raise SystemExit(1)
ids = [x["id"] for x in embedded[:2]]

# ── 1. Save / list / caps / author scoping ────────────────────────────────────
payload = {
    "question": "Verification: what do the sources agree on?",
    "answer_text": "They agree on effort [SOURCE:abc]. They differ on scope.",
    "source_ids": ids,
    "citations": [
        {"chunk_id": "c" * 36, "source_id": ids[0], "locator": "para:1", "excerpt": "effort matters"},
        {"chunk_id": "d" * 36, "source_id": ids[1], "locator": "ts:00:01:33", "excerpt": "scope differs"},
    ],
}
s, saved = call("POST", f"/v1/kbs/{KB}/syntheses", dev, payload)
check("save synthesis → 201", s == 201 and saved.get("id"), (s, saved))
SYN = saved["id"] if s == 201 else None

s, rows = call("GET", f"/v1/kbs/{KB}/syntheses", dev)
check("list shows the saved row with citations", s == 200 and any(
    r["id"] == SYN and len(r["citations"]) == 2 for r in rows), (s, rows))

s, _ = call("POST", f"/v1/kbs/{KB}/syntheses", dev, {**payload, "source_ids": ids[:1]})
check("save with 1 source → 422", s == 422, s)
s, _ = call("POST", f"/v1/kbs/{KB}/syntheses", dev, {**payload, "answer_text": "x" * 50_001})
check("answer over cap → 422", s == 422, s)

s, _ = call("GET", f"/v1/kbs/{KB}/syntheses", tester)
check("tester list on dev's private KB → 404", s == 404, s)
s, _ = call("DELETE", f"/v1/kbs/{KB}/syntheses/{SYN}", tester)
check("tester delete of dev's synthesis → 404", s == 404, s)

# ── 2. Board projection ───────────────────────────────────────────────────────
s, board = call("POST", "/v1/boards", dev, {"title": f"synth-verify-{int(time.time())}"})
check("board created", s in (200, 201), (s, board))
BOARD = board["id"]

s, item = call("POST", f"/v1/boards/{BOARD}/syntheses", dev, {"synthesis_id": SYN})
check("projection → 201 synthesis item", s == 201 and item["source"]["type"] == "synthesis", (s, item))
proj_source = item["source_id"]

status = wait_source(proj_source, dev)
check("projected doc embedded", status == "embedded", status)

s, src = call("GET", f"/v1/sources/{proj_source}", dev)
BOARD_KB = src.get("kb_id") if s == 200 else None
s, hits = call("GET", f"/v1/kbs/{BOARD_KB}/search?q=agree%20on%20effort&mode=keyword&limit=5", dev)
check("board-KB keyword search finds the answer", s == 200 and len(hits) > 0
      and any(h["source_id"] == proj_source for h in hits), (s, hits))

s, item2 = call("POST", f"/v1/boards/{BOARD}/syntheses", dev, {"synthesis_id": SYN})
check("re-add reuses the Source (idempotent)", s == 201 and item2["source_id"] == proj_source,
      (s, item2.get("source_id") if s == 201 else item2))

s, _ = call("POST", f"/v1/boards/{BOARD}/syntheses", tester, {"synthesis_id": SYN})
check("tester projection on dev board → 404", s == 404, s)

# ── 3. Enqueue-race regression: two rapid board URL adds ──────────────────────
s1, i1 = call("POST", f"/v1/boards/{BOARD}/sources", dev,
              {"source_url": "https://example.com/", "note": "", "lane": ""})
s2, i2 = call("POST", f"/v1/boards/{BOARD}/sources", dev,
              {"source_url": "https://example.org/", "note": "", "lane": ""})
check("two rapid board adds accepted", s1 == 201 and s2 == 201, (s1, s2))
st1 = wait_source(i1["source_id"], dev, timeout=120)
st2 = wait_source(i2["source_id"], dev, timeout=120)
check("neither source stuck pending (race fixed)",
      st1 in ("embedded", "failed") and st2 in ("embedded", "failed"), (st1, st2))

# ── 4. Delete ────────────────────────────────────────────────────────────────
s, _ = call("DELETE", f"/v1/kbs/{KB}/syntheses/{SYN}", dev)
check("author delete → 204", s == 204, s)
s, rows = call("GET", f"/v1/kbs/{KB}/syntheses", dev)
check("row gone after delete", s == 200 and all(r["id"] != SYN for r in rows))

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} checks passed")
raise SystemExit(1 if fails else 0)
