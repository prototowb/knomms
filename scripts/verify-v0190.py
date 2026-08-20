"""Live verification for v0.19.0 — bundle feeds & subscriptions (docs/23 §7).

Loop-back federation on one host: dev federates a KB; tester subscribes to
the feed THROUGH the real nginx chain (the api container fetches
http://nginx/... exactly as a remote peer would), getting a private
read-only mirror; sync detects changes after the origin grows.
"""

import json, time, urllib.request, urllib.error

BASE = "http://localhost/api"
INTERNAL_FEED_BASE = "http://nginx/api/v1/federation"  # reachable from inside the api container
results = []


def call(method, path, token=None, body=None, base=BASE):
    req = urllib.request.Request(base + path, method=method)
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


def wait_sources_embedded(kb_id, token, expect=None, timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        s, srcs = call("GET", f"/kb/{kb_id}/sources", token)
        if s == 200 and srcs and all(x["ingestion_status"] in ("embedded", "failed") for x in srcs):
            if expect is None or len(srcs) == expect:
                return srcs
        time.sleep(5)
    return None


dev = login("dev@localhost.dev", "devdev99")
tester = login("test@example.com", "password123")

# ── Setup ─────────────────────────────────────────────────────────────────────
s, kbs = call("GET", "/kbs", dev)
KB = None
for kb in kbs:
    s, srcs = call("GET", f"/kb/{kb['id']}/sources", dev)
    if s == 200 and sum(1 for x in srcs if x["ingestion_status"] == "embedded") >= 2:
        KB, origin_count = kb["id"], len(srcs)
        break
check("setup: origin KB found", KB is not None)

# ── 1. Feed lifecycle (OQ-95) ─────────────────────────────────────────────────
s, feed = call("POST", f"/v1/kbs/{KB}/federation", dev)
check("owner enables feed", s == 201 and len(feed["slug"]) >= 40, (s, feed))
SLUG = feed["slug"]
s, feed2 = call("POST", f"/v1/kbs/{KB}/federation", dev)
check("re-enable is idempotent (same slug)", s == 201 and feed2["slug"] == SLUG, (s, feed2))
s, _ = call("POST", f"/v1/kbs/{KB}/federation", tester)
check("non-owner enable → 404", s == 404, s)

s, meta = call("GET", f"/v1/federation/{SLUG}/meta")  # no auth header
check("unauthenticated meta fetch works", s == 200 and len(meta["bundle_hash"]) == 64, (s, meta))
s, bundle = call("GET", f"/v1/federation/{SLUG}")
check("unauthenticated bundle fetch works", s == 200 and bundle["format"] == "knomms-kb-bundle", s)
s, _ = call("GET", "/v1/federation/definitely-not-a-real-slug-000000000000/meta")
check("unknown slug → 404", s == 404, s)

# ── 2. Subscribe (OQ-96) — tester mirrors dev's feed through nginx ────────────
s, sub = call("POST", "/v1/federation/subscriptions", tester,
              {"feed_url": f"{INTERNAL_FEED_BASE}/{SLUG}"})
check("tester subscribes through the real chain", s == 201, (s, sub))
MIRROR, SUB = sub["kb_id"], sub["id"]
srcs = wait_sources_embedded(MIRROR, tester, expect=origin_count, timeout=60)
check("mirror embedded immediately (model match)", srcs is not None
      and all(x["ingestion_status"] == "embedded" for x in srcs), srcs and [x["ingestion_status"] for x in srcs])
# Derive the query from the bundle itself — corpus-independent
import re as _re
from urllib.parse import quote as _quote
words = [w for w in _re.findall(r"[A-Za-z]{7,}", bundle["chunks"][0]["text"])]
query = words[0] if words else bundle["chunks"][0]["text"].split()[0]
s, hits = call("GET", f"/v1/kbs/{MIRROR}/search?q={_quote(query)}&mode=keyword&limit=3", tester)
check("mirror search works for the subscriber", s == 200 and len(hits) > 0, (s, query, hits))
s, _ = call("POST", "/v1/federation/subscriptions", tester, {"feed_url": "ftp://nope/feed"})
check("bad scheme → 422", s == 422, s)

# ── 3. Sync (OQ-97) ───────────────────────────────────────────────────────────
s, res = call("POST", f"/v1/federation/subscriptions/{SUB}/sync", tester)
check("unchanged sync → changed:false", s == 200 and res["changed"] is False, (s, res))
s, _ = call("POST", f"/v1/federation/subscriptions/{SUB}/sync", dev)
check("foreign subscription sync → 404", s == 404, s)

s, newsrc = call("POST", "/v1/sources/", dev, {"url": "https://example.com/", "kb_id": KB})
check("origin gains a source", s == 202, (s, newsrc))
grown = wait_sources_embedded(KB, dev, expect=origin_count + 1, timeout=120)
check("origin source embedded", grown is not None)

s, res = call("POST", f"/v1/federation/subscriptions/{SUB}/sync", tester)
check("changed sync re-materializes", s == 200 and res["changed"] is True
      and res["source_count"] == origin_count + 1, (s, res))
srcs = wait_sources_embedded(MIRROR, tester, expect=origin_count + 1, timeout=60)
check("mirror now has the new source", srcs is not None and len(srcs) == origin_count + 1,
      srcs and len(srcs))

# ── 4. Mirror read-only (OQ-98) + unsubscribe escape hatch ────────────────────
s, d = call("POST", "/v1/sources/", tester, {"url": "https://example.org/", "kb_id": MIRROR})
check("mirror add-source → 422 read-only", s == 422 and "mirror" in str(d), (s, d))
s, _ = call("DELETE", f"/v1/federation/subscriptions/{SUB}", tester)
check("unsubscribe → 204", s == 204, s)
s, d = call("POST", "/v1/sources/", tester, {"url": "https://example.org/", "kb_id": MIRROR})
check("freed KB accepts sources again", s == 202, (s, d))

# ── 5. Revoke (OQ-95 rotation) ────────────────────────────────────────────────
s, _ = call("DELETE", f"/v1/kbs/{KB}/federation", dev)
check("owner revokes feed", s == 204, s)
s, _ = call("GET", f"/v1/federation/{SLUG}/meta")
check("revoked slug → 404", s == 404, s)
s, d = call("POST", "/v1/federation/subscriptions", tester,
            {"feed_url": f"{INTERNAL_FEED_BASE}/{SLUG}"})
check("subscribe to revoked feed fails cleanly (502)", s == 502, (s, d))

# ── 6. Part-1 import regression (bundle_io refactor) ──────────────────────────
s, exported = call("GET", f"/v1/kbs/{KB}/export", dev)
check("export still works", s == 200 and exported["format"] == "knomms-kb-bundle", s)

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} checks passed")
raise SystemExit(1 if fails else 0)
