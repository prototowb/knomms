"""Live verification for v0.13.0 — multi-source synthesis (docs/16 §7).

Uses (or builds) a dev-owned KB with ≥2 embedded sources — the v0.12.0
verify KB (video + Wikipedia page) qualifies. Streams a real synthesis
through the nginx→Nuxt BFF→FastAPI chain; on CPU the generation takes
2–5 minutes. Guard checks are instant.
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
            return r.status, json.loads(r.read() or b"null")
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

# ── Setup: find a dev KB with ≥2 embedded sources ─────────────────────────────
s, kbs = call("GET", "/kbs", dev)
assert s == 200, (s, kbs)
KB = None
embedded = []
for kb in kbs:
    s, srcs = call("GET", f"/kb/{kb['id']}/sources", dev)
    if s != 200:
        continue
    emb = [x for x in srcs if x["ingestion_status"] == "embedded"]
    if len(emb) >= 2:
        KB, embedded = kb["id"], emb
        break
check("setup: KB with ≥2 embedded sources found", KB is not None, [k.get("title") for k in kbs])
if KB is None:
    print("No suitable KB — run verify-v0120.py first (it builds one)."); raise SystemExit(1)

ids = [x["id"] for x in embedded[:2]]
has_video = any(x["type"] == "video" for x in embedded[:2])
check("selection includes a video source", has_video, [x["type"] for x in embedded[:2]])

# ── 1. Guards (instant) ───────────────────────────────────────────────────────
s, d = call("POST", f"/v1/kbs/{KB}/synthesize", dev, {"question": "q", "source_ids": ids[:1]})
check("<2 sources → 422", s == 422, (s, d))
s, d = call("POST", f"/v1/kbs/{KB}/synthesize", dev,
            {"question": "q", "source_ids": [ids[0], "00000000-0000-0000-0000-000000000000"]})
check("foreign source id → 422", s == 422, (s, d))
s, d = call("POST", f"/v1/kbs/{KB}/synthesize", dev, {"question": "q", "source_ids": [ids[0], ids[0]]})
check("duplicate source ids → 422", s == 422, (s, d))
s, d = call("POST", "/v1/kbs/00000000-0000-0000-0000-000000000000/synthesize", dev,
            {"question": "q", "source_ids": ids})
check("unknown KB → 404", s == 404, (s, d))

# ── 2. Streamed synthesis through the BFF chain ───────────────────────────────
question = "What do these sources say about following your interests, and where do they differ?"
req = urllib.request.Request(f"{BASE}/kb/{KB}/synthesize", method="POST")
req.add_header("Content-Type", "application/json")
req.add_header("Authorization", f"Bearer {dev}")
started = time.time()
citations = None
tokens = []
try:
    with urllib.request.urlopen(req, data=json.dumps({"question": question, "source_ids": ids}).encode(),
                                timeout=600) as resp:
        buffer = ""
        while True:
            chunk = resp.read(1)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")
            while "\n\n" in buffer:
                event, buffer = buffer.split("\n\n", 1)
                etype, data = "message", ""
                for line in event.split("\n"):
                    if line.startswith("event:"):
                        etype = line[len("event:"):].strip()
                    elif line.startswith("data:"):
                        raw = line[len("data:"):]
                        data = raw[1:] if raw.startswith(" ") else raw
                if etype == "citations":
                    citations = json.loads(data)
                elif data:
                    tokens.append(data)
except Exception as exc:
    check("synthesis stream completed", False, repr(exc))
else:
    answer = "".join(tokens)
    elapsed = int(time.time() - started)
    print(f"  [stream done in {elapsed}s, {len(answer)} chars, {len(citations or {})} citations]", flush=True)
    check("citations event received first", citations is not None and len(citations) > 0)
    if citations:
        cited_sources = {c["source_id"] for c in citations.values()}
        check("citations span both selected sources (balanced retrieval)",
              set(ids) <= cited_sources, (sorted(cited_sources), ids))
        video_locators = [c["locator"] for c in citations.values() if c["locator"].startswith("ts:")]
        check("video chunks carry ts: locators in citations", not has_video or len(video_locators) > 0,
              video_locators)
    check("answer streamed", len(answer) > 100, len(answer))
    import re
    # Accept both the prompt contract [SOURCE:uuid] and the bare [uuid] the
    # local model sometimes emits — both render as citation chips
    inline = set(re.findall(r"\[(?:SOURCE:)?([a-f0-9\-]{36})\]", answer))
    check("answer cites inline (either notation)", len(inline) > 0, answer[:200])
    if citations and inline:
        check("no hallucinated citation ids", inline <= set(citations.keys()),
              sorted(inline - set(citations.keys())))

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} checks passed")
raise SystemExit(1 if fails else 0)
