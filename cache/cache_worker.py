import json
from datetime import date
from pathlib import Path

CACHE_FILE = Path("cache/summary_cache.json")


def load_cache():
    """Load cache from disk if it exists."""
    
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r") as f:
            return json.load(f)

    return {}


def save_cache(cache):
    """Persist cache dictionary to disk."""

    CACHE_FILE.parent.mkdir(exist_ok=True)

    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def get_cached_summary(cache, journey_id):
    """Return cached summary if available."""

    journey_id = str(journey_id)

    if journey_id in cache:
        return cache[journey_id]["summary"]

    return None


def store_summary(cache, journey_id, driver_name, summary):
    """Store a new summary in the cache."""

    journey_id = str(journey_id)

    cache[journey_id] = {
        "driver": driver_name,
        "summary": summary,
        "generated_at": str(date.today())
    }