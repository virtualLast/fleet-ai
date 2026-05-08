from typing import Dict, Any, Optional, List
import hashlib
import json
import re
from datetime import date
from pathlib import Path

# Per-journey summary cache (single driver summary responses).
CACHE_FILE = Path("cache/summary_cache.json")

# Collection summary cache (POST collection scope responses).
EVENT_COLLECTION_CACHE_FILE = Path("cache/event-collection-summary.json")

# Deterministic cache schema version for collection-based behaviour summaries.
CACHE_SCHEMA_VERSION = "v1"

# Filesystem cache directory for behaviour summaries (`{sha256}.json`).
DRIVER_BEHAVIOUR_CACHE_DIR = Path("cache/driver_behaviour")
SHA256_HEX_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def load_cache() -> Dict[str, Any]:
    """Load cache from the disk if it exists."""
    
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r") as f:
            return json.load(f)

    return {}


def save_cache(cache: Dict[str, Any]):
    """Persist cache dictionary to disk."""

    CACHE_FILE.parent.mkdir(exist_ok=True)

    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def load_event_collection_cache() -> Dict[str, Any]:
    """Load event collection summary cache from the disk if it exists."""

    if EVENT_COLLECTION_CACHE_FILE.exists():
        with open(EVENT_COLLECTION_CACHE_FILE, "r") as f:
            return json.load(f)

    return {}


def save_event_collection_cache(cache: Dict[str, Any]):
    """Persist event collection summary cache dictionary to disk."""

    EVENT_COLLECTION_CACHE_FILE.parent.mkdir(exist_ok=True)

    with open(EVENT_COLLECTION_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def get_cached_summary(cache: Dict[str, Any], journey_id: int) -> Optional[str]:
    """Return a cached summary if available."""

    # JSON object keys are strings, so normalize integer ids before lookup.
    s_journey_id = str(journey_id)

    if s_journey_id in cache:
        return cache[s_journey_id]["summary"]

    return None


def store_summary(cache: Dict[str, Any], journey_id: int, driver_name: str, summary: str):
    """Store a new summary in the cache."""

    # Keep cache key format aligned with `get_cached_summary` lookups.
    s_journey_id = str(journey_id)

    cache[s_journey_id] = {
        "driver": driver_name,
        "summary": summary,
        "generated_at": str(date.today())
    }


def get_cached_event_collection_summary(cache: Dict[str, Any], collection_scope: str) -> Optional[Dict[str, Any]]:
    """Return a cached collection summary for the provided scope key."""

    return cache.get(collection_scope)


def store_event_collection_summary(
    cache: Dict[str, Any],
    collection_scope: str,
    driver_ids: List[int],
    summary: str,
):
    """Store a collection summary in cache, including generation metadata."""

    cache[collection_scope] = {
        "collection_scope": collection_scope,
        "driver_ids": driver_ids,
        "summary": summary,
        "generated_at": str(date.today())
    }


def build_driver_behaviour_cache_key(hash_source: Dict[str, Any]) -> str:
    """Return deterministic SHA256 key for normalized behaviour summary payloads."""

    serialized_source = json.dumps(hash_source, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized_source.encode("utf-8")).hexdigest()


def _driver_behaviour_cache_file(cache_key: str) -> Path:
    """Return cache file path for a behaviour summary cache key."""

    if not SHA256_HEX_PATTERN.fullmatch(cache_key):
        raise ValueError("Invalid cache_key: expected 64-char SHA256 hex digest")

    return DRIVER_BEHAVIOUR_CACHE_DIR / f"{cache_key}.json"


def load_driver_behaviour_cache_entry(cache_key: str) -> Optional[Dict[str, Any]]:
    """Load a behaviour summary cache entry by deterministic cache key."""

    cache_file = _driver_behaviour_cache_file(cache_key)

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, "r") as file:
            entry = json.load(file)
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(entry, dict):
        return None

    if entry.get("cache_version") != CACHE_SCHEMA_VERSION:
        return None

    return entry


def store_driver_behaviour_cache_entry(cache_key: str, entry: Dict[str, Any]):
    """Store a behaviour summary cache entry as `cache/driver_behaviour/{sha256}.json`."""

    DRIVER_BEHAVIOUR_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _driver_behaviour_cache_file(cache_key)
    cache_entry = dict(entry)
    cache_entry["cache_version"] = CACHE_SCHEMA_VERSION

    with open(cache_file, "w") as file:
        json.dump(cache_entry, file, indent=2, sort_keys=True)