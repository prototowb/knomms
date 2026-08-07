"""Live verification for v0.12.0 — video transcript ingestion (docs/15 §7).

Runs against the Colima stack via the BFF /api/v1 catch-all. Ingests a
captioned YouTube video end-to-end (transcript → chunks with ts: locators →
search with deep-link fields → curriculum grounding), checks the
caption-less/unavailable failure path, and regression-checks web URL typing.
Curriculum generation takes minutes on CPU — expect a ~5-minute run.
"""

import json, time, urllib.request, urllib.error

BASE = "http://localhost/api"
results = []

VIDEO_URL = "https://www.youtube.com/watch?v=UF8uR6Z6KLc"  # Steve Jobs Stanford address — captioned
BAD_VIDEO_URL = "https://www.youtube.com/watch?v=aaaaaaaaaaa"  # valid shape, no such video
WEB_URL = "https://en.wikipedia.org/wiki/Commencement_speech"


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

# ── Setup: fresh KB ───────────────────────────────────────────────────────────
s, kb = call("POST", "/v1/kbs", dev, {"title": f"video-verify-{int(time.time())}"})
check("setup: KB created", s in (200, 201), (s, kb))
KB = kb["id"]

# ── 1. Captioned video end-to-end ─────────────────────────────────────────────
s, src = call("POST", "/v1/sources/", dev, {"url": VIDEO_URL, "kb_id": KB})
check("submit video URL → 202", s == 202, (s, src))
check("source typed video", src.get("type") == "video", src)
check("oEmbed title resolved", bool(src.get("title")) and src["title"] not in ("watch", f"youtube:UF8uR6Z6KLc"), src.get("title"))

status = wait_source(src["id"], dev)
check("video ingestion embedded", status == "embedded", status)

s, hits = call("GET", f"/v1/kbs/{KB}/search?q=connect%20the%20dots&mode=keyword&limit=5", dev)
check("keyword search returns video chunk", s == 200 and len(hits) > 0, (s, hits))
if hits:
    h = hits[0]
    check("chunk locator is ts:HH:MM:SS", h["locator"].startswith("ts:") and len(h["locator"]) == 11, h["locator"])
    check("search result carries source_url + type video",
          h["source_type"] == "video" and h["source_url"] == VIDEO_URL, h)

s, hits2 = call("GET", f"/v1/kbs/{KB}/search?q=what%20should%20I%20do%20with%20my%20life&mode=semantic&limit=3", dev)
check("semantic search over transcript works", s == 200 and len(hits2) > 0, (s, hits2))

# ── 2. Unavailable/caption-less video fails cleanly ───────────────────────────
s, bad = call("POST", "/v1/sources/", dev, {"url": BAD_VIDEO_URL, "kb_id": KB})
check("bad video accepted for processing (typed video)", s == 202 and bad.get("type") == "video", (s, bad))
status = wait_source(bad["id"], dev, timeout=90)
check("bad video ingestion → failed", status == "failed", status)

# ── 3. Web regression: ordinary URLs still typed web_page ─────────────────────
s, web = call("POST", "/v1/sources/", dev, {"url": WEB_URL, "kb_id": KB})
check("web URL still typed web_page", s == 202 and web.get("type") == "web_page", (s, web))

# ── 4. Curriculum grounding over the video corpus ─────────────────────────────
s, path = call("POST", f"/v1/kbs/{KB}/learning-paths", dev,
               {"learning_goal": "Understand the main lessons of the speech"})
check("curriculum job accepted (202)", s == 202, (s, path))
if s == 202:
    deadline = time.time() + 600
    pstatus = "generating"
    while time.time() < deadline and pstatus == "generating":
        time.sleep(10)
        s, p = call("GET", f"/learning-paths/{path['id']}", dev)
        pstatus = p.get("status") if s == 200 else pstatus
    check("curriculum completed (draft)", pstatus == "draft", pstatus)
    if pstatus == "draft":
        passages = [sp for c in p["concepts"] for sp in (c["source_passages"] or [])]
        check("concept passages carry ts: locators",
              len(passages) > 0 and all(sp["locator"].startswith("ts:") for sp in passages),
              [sp.get("locator") for sp in passages[:5]])

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} checks passed")
raise SystemExit(1 if fails else 0)
