"""Live verification for v0.15.0 — portable KB bundles (docs/18 §7).

Round-trips the video+web verify KB: export (owner-only) → import →
instant embeddings + preserved ts: locators + working semantic search;
tamper 422s; stripped-embeddings import exercising the import.jobs
re-embed worker.
"""

import copy, json, time, urllib.request, urllib.error

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


def upload(path, token, payload_bytes, filename="bundle.knomms.json"):
    boundary = "----knommsverify"
    body = (
        (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
         f'filename="{filename}"\r\nContent-Type: application/json\r\n\r\n').encode()
        + payload_bytes
        + f"\r\n--{boundary}--\r\n".encode()
    )
    req = urllib.request.Request(BASE + path, method="POST", data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as r:
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
tester = login("test@example.com", "password123")

# ── Setup: the video+web verify KB ────────────────────────────────────────────
s, kbs = call("GET", "/kbs", dev)
KB = None
for kb in kbs:
    s, srcs = call("GET", f"/kb/{kb['id']}/sources", dev)
    if s == 200 and sum(1 for x in srcs if x["ingestion_status"] == "embedded") >= 2 \
            and any(x["type"] == "video" for x in srcs):
        KB = kb["id"]
        break
check("setup: source KB found (video + web)", KB is not None)
if KB is None:
    raise SystemExit(1)

# ── 1. Export ─────────────────────────────────────────────────────────────────
s, bundle = call("GET", f"/v1/kbs/{KB}/export", dev)
check("owner export → 200 bundle", s == 200 and bundle.get("format") == "knomms-kb-bundle", s)
check("bundle carries embeddings + model id", any(
    c.get("embedding") and c.get("embedding_model_id") for c in bundle["chunks"]))
check("bundle preserves ts: locators", any(
    c["locator"].startswith("ts:") for c in bundle["chunks"]))
check("no instance ids in bundle sources", all("id" not in s_ for s_ in bundle["sources"]))
s, _ = call("GET", f"/v1/kbs/{KB}/export", tester)
check("non-owner export → 404", s == 404, s)

# ── 2. Import round-trip (instant embeddings) ─────────────────────────────────
s, imp = upload("/v1/kbs/import", dev, json.dumps(bundle).encode())
check("import → 201", s == 201, (s, imp))
check("no reindex needed (model match)", imp and imp["reindexing"] is False, imp)
check("counts match", imp and imp["source_count"] == len(bundle["sources"])
      and imp["chunk_count"] == len(bundle["chunks"]), imp)
NEW = imp["kb_id"]

s, srcs = call("GET", f"/kb/{NEW}/sources", dev)
check("imported sources embedded immediately", s == 200 and len(srcs) == len(bundle["sources"])
      and all(x["ingestion_status"] == "embedded" for x in srcs), (s, srcs))
check("source types preserved (video)", any(x["type"] == "video" for x in srcs))

s, hits = call("GET", f"/v1/kbs/{NEW}/search?q=follow%20your%20heart&mode=semantic&limit=5", dev)
check("semantic search works on imported KB (vectors live)", s == 200 and len(hits) > 0, (s, hits))
s, hits_kw = call("GET", f"/v1/kbs/{NEW}/search?q=connect%20the%20dots&mode=keyword&limit=5", dev)
check("imported chunks keep ts: locators", s == 200 and any(
    h["locator"].startswith("ts:") for h in hits_kw), (s, hits_kw))

# ── 3. Tamper 422s ────────────────────────────────────────────────────────────
bad = copy.deepcopy(bundle); bad["version"] = 99
s, d = upload("/v1/kbs/import", dev, json.dumps(bad).encode())
check("wrong version → 422", s == 422, (s, d))
bad = copy.deepcopy(bundle); bad["chunks"][0]["embedding"] = [0.1, 0.2]
s, d = upload("/v1/kbs/import", dev, json.dumps(bad).encode())
check("bad embedding dims → 422", s == 422, (s, d))
bad = copy.deepcopy(bundle); bad["chunks"][0]["source_idx"] = 999
s, d = upload("/v1/kbs/import", dev, json.dumps(bad).encode())
check("out-of-range source_idx → 422", s == 422, (s, d))
s, d = upload("/v1/kbs/import", dev, b"definitely not json {")
check("non-JSON → 422", s == 422, (s, d))

# ── 4. Stripped embeddings → import.jobs re-embed ─────────────────────────────
stripped = copy.deepcopy(bundle)
for c in stripped["chunks"]:
    c["embedding"] = None
    c["embedding_model_id"] = None
s, imp2 = upload("/v1/kbs/import", dev, json.dumps(stripped).encode())
check("stripped import → 201 with reindexing", s == 201 and imp2["reindexing"] is True, (s, imp2))
NEW2 = imp2["kb_id"]

deadline = time.time() + 180
done = False
while time.time() < deadline:
    s, srcs2 = call("GET", f"/kb/{NEW2}/sources", dev)
    if s == 200 and srcs2 and all(x["ingestion_status"] == "embedded" for x in srcs2):
        done = True
        break
    time.sleep(5)
check("worker re-embedded stripped import", done)
s, hits2 = call("GET", f"/v1/kbs/{NEW2}/search?q=follow%20your%20heart&mode=semantic&limit=5", dev)
check("semantic search works after re-embed", s == 200 and len(hits2) > 0, (s, hits2))

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} checks passed")
raise SystemExit(1 if fails else 0)
