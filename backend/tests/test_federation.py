"""Unit tests for federation pure seams — hash, URL guard, sync decision (KC-119/120)."""

from app.domains.federation.service import check_feed_url, should_sync
from app.domains.knowledge_base.bundles import canonical_bundle_hash


def test_hash_stable_and_key_order_independent():
    a = {"format": "knomms-kb-bundle", "version": 1, "kb": {"title": "t"}, "sources": [], "chunks": []}
    b = {"chunks": [], "sources": [], "kb": {"title": "t"}, "version": 1, "format": "knomms-kb-bundle"}
    assert canonical_bundle_hash(a) == canonical_bundle_hash(b)
    assert len(canonical_bundle_hash(a)) == 64


def test_hash_changes_with_content():
    a = {"kb": {"title": "t"}, "chunks": [{"text": "x"}]}
    b = {"kb": {"title": "t"}, "chunks": [{"text": "y"}]}
    assert canonical_bundle_hash(a) != canonical_bundle_hash(b)


def test_feed_url_guard():
    assert check_feed_url("https://peer.example.com/api/v1/federation/abc") is None
    assert check_feed_url("http://localhost/api/v1/federation/abc") is None
    assert "http(s)" in check_feed_url("ftp://x/feed")
    assert "http(s)" in check_feed_url("file:///etc/passwd")
    assert check_feed_url("https://") is not None
    assert check_feed_url("not a url") is not None


def test_should_sync_decision():
    assert should_sync("a" * 64, {"bundle_hash": "b" * 64}) is True
    assert should_sync("a" * 64, {"bundle_hash": "a" * 64}) is False
    assert should_sync("a" * 64, {}) is True                    # missing → fetch + validate
    assert should_sync("a" * 64, {"bundle_hash": 42}) is True   # garbage → fetch + validate
