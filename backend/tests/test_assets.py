"""Unit tests for asset domain — pure logic, no DB or Ollama."""

import hashlib

from app.domains.assets.service import compute_content_hash, next_version_num


# ── compute_content_hash ──────────────────────────────────────────────────────


def test_content_hash_is_sha256_hex():
    content = "You are a helpful assistant."
    expected = hashlib.sha256(content.encode()).hexdigest()
    assert compute_content_hash(content) == expected


def test_content_hash_length():
    # SHA-256 produces 64 hex characters
    assert len(compute_content_hash("anything")) == 64


def test_content_hash_deterministic():
    content = "system prompt v1"
    assert compute_content_hash(content) == compute_content_hash(content)


def test_content_hash_differs_for_different_content():
    assert compute_content_hash("prompt A") != compute_content_hash("prompt B")


def test_content_hash_unicode():
    # Non-ASCII content should hash without error
    result = compute_content_hash("Ünïcödé prömpt 🤖")
    assert len(result) == 64


# ── next_version_num ──────────────────────────────────────────────────────────


def test_next_version_num_empty_returns_one():
    assert next_version_num([]) == 1


def test_next_version_num_sequential():
    assert next_version_num([1]) == 2
    assert next_version_num([1, 2]) == 3
    assert next_version_num([1, 2, 3]) == 4


def test_next_version_num_out_of_order():
    # Should still be max + 1, not len + 1
    assert next_version_num([3, 1, 2]) == 4


def test_next_version_num_does_not_mutate():
    nums = [1, 2, 3]
    next_version_num(nums)
    assert nums == [1, 2, 3]


def test_next_version_num_single_high():
    assert next_version_num([99]) == 100
