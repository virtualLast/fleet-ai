from pathlib import Path

import pytest

from cache import cache_worker


def test_driver_behaviour_cache_helpers_reject_invalid_cache_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_worker, "DRIVER_BEHAVIOUR_CACHE_DIR", Path(tmp_path))

    with pytest.raises(ValueError):
        cache_worker.load_driver_behaviour_cache_entry("../invalid")

    with pytest.raises(ValueError):
        cache_worker.store_driver_behaviour_cache_entry("invalid", {"summary": "x"})


def test_driver_behaviour_cache_helpers_store_and_validate_schema_version(tmp_path, monkeypatch):
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