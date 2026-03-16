from typing import Dict, Any, Optional
import json
from datetime import date
from pathlib import Path

CACHE_FILE = Path("cache/summary_cache.json")


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


def get_cached_summary(cache: Dict[str, Any], journey_id: int) -> Optional[str]:
    """Return a cached summary if available."""

    s_journey_id = str(journey_id)

    if s_journey_id in cache:
        return cache[s_journey_id]["summary"]

    return None


def store_summary(cache: Dict[str, Any], journey_id: int, driver_name: str, summary: str):
    """Store a new summary in the cache."""

    s_journey_id = str(journey_id)

    cache[s_journey_id] = {
        "driver": driver_name,
        "summary": summary,
        "generated_at": str(date.today())
    }