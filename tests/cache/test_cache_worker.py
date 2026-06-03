from pathlib import Path

import pytest

from cache import cache_worker


def test_driver_behaviour_cache_helpers_reject_invalid_cache_keys(tmp_path, monkeypatch):
    """What: Verify driver-behaviour cache helpers reject malformed keys.

    Why: Cache helpers must enforce key integrity to prevent path traversal and invalid files.
    How: Patch cache dir and assert invalid key operations raise `ValueError`.
    """
    monkeypatch.setattr(cache_worker, "DRIVER_BEHAVIOUR_CACHE_DIR", Path(tmp_path))

    with pytest.raises(ValueError):
        cache_worker.load_driver_behaviour_cache_entry("../invalid")

    with pytest.raises(ValueError):
        cache_worker.store_driver_behaviour_cache_entry("invalid", {"summary": "x"})


def test_driver_behaviour_cache_helpers_store_and_validate_schema_version(tmp_path, monkeypatch):
    """What: Verify driver-behaviour cache entries persist and enforce schema version.

    Why: Version checks prevent stale cache payloads from being reused after schema changes.
    How: Store/load valid entry, then write stale version payload and assert cache miss.
    """
    monkeypatch.setattr(cache_worker, "DRIVER_BEHAVIOUR_CACHE_DIR", Path(tmp_path))
    cache_key = "a" * 64

    cache_worker.store_driver_behaviour_cache_entry(cache_key, {"summary": "stored"})
    loaded = cache_worker.load_driver_behaviour_cache_entry(cache_key)

    assert loaded is not None
    assert loaded["summary"] == "stored"
    assert loaded["cache_version"] == cache_worker.CACHE_SCHEMA_VERSION

    cache_file = Path(tmp_path) / f"{cache_key}.json"
    cache_file.write_text('{"cache_version":"v0","summary":"stale"}')

    stale_loaded = cache_worker.load_driver_behaviour_cache_entry(cache_key)
    assert stale_loaded is None


def test_fleet_summary_cache_helpers_reject_invalid_keys(tmp_path, monkeypatch):
    """What: Verify fleet-summary cache helpers reject invalid cache keys.

    Why: Fleet cache APIs should fail fast on malformed key formats.
    How: Patch cache file path and assert get/set invalid-key calls raise `ValueError`.
    """
    monkeypatch.setattr(cache_worker, "EVENT_COLLECTION_CACHE_FILE", Path(tmp_path) / "event-collection-summary.json")

    with pytest.raises(ValueError):
        cache_worker.get_fleet_summary_cache("invalid")

    with pytest.raises(ValueError):
        cache_worker.set_fleet_summary_cache("invalid", {"summary": "x"})


def test_fleet_summary_cache_helpers_store_and_load(tmp_path, monkeypatch):
    """What: Verify fleet-summary cache helper round-trip storage works.

    Why: Persisted fleet summaries must be retrievable with metadata intact.
    How: Build key, store summary, load entry, and assert key fields are present.
    """
    monkeypatch.setattr(cache_worker, "EVENT_COLLECTION_CACHE_FILE", Path(tmp_path) / "event-collection-summary.json")

    cache_key = cache_worker.build_fleet_summary_cache_key(
        "scope-a",
        [{"id": 1, "dsmEventsCount": 2}],
    )

    stored = cache_worker.set_fleet_summary_cache(cache_key, {"summary": "fleet summary"})
    loaded = cache_worker.get_fleet_summary_cache(cache_key)

    assert loaded is not None
    assert loaded["summary"] == "fleet summary"
    assert loaded["cache_key"] == cache_key
    assert "generated_at" in stored


def test_fleet_summary_cache_helpers_respect_ttl_expiry(tmp_path, monkeypatch):
    """What: Verify fleet-summary cache retrieval honors TTL expiry.

    Why: Expired summaries should not be served as current data.
    How: Seed old `generated_at` entry and assert retrieval with short TTL returns `None`.
    """
    monkeypatch.setattr(cache_worker, "EVENT_COLLECTION_CACHE_FILE", Path(tmp_path) / "event-collection-summary.json")

    cache_key = f"{cache_worker.FLEET_SUMMARY_CACHE_PREFIX}:{'a' * 64}"
    cache_worker.save_event_collection_cache(
        {
            cache_key: {
                "cache_key": cache_key,
                "summary": "old summary",
                "generated_at": "2000-01-01T00:00:00Z",
            }
        }
    )

    loaded = cache_worker.get_fleet_summary_cache(cache_key, ttl=1)

    assert loaded is None
