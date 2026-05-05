from typing import Dict, Any, Optional, List
import json
from datetime import date
from pathlib import Path

# Per-journey summary cache (single driver summary responses).
CACHE_FILE = Path("cache/summary_cache.json")

# Collection summary cache (POST collection scope responses).
EVENT_COLLECTION_CACHE_FILE = Path("cache/event-collection-summary.json")


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