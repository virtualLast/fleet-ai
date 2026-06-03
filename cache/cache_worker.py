import hashlib
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Collection summary cache (POST collection scope responses).
EVENT_COLLECTION_CACHE_FILE = Path("cache/event-collection-summary.json")

# Deterministic cache schema version for collection-based behaviour summaries.
CACHE_SCHEMA_VERSION = "v2"

FLEET_SUMMARY_CACHE_PREFIX = "fleet_summary"


def _get_default_fleet_summary_ttl_seconds() -> int:
    """Return fleet-summary TTL default from env with safe fallback."""

    raw_value = os.getenv("FLEET_SUMMARY_CACHE_TTL_SECONDS", "3600")

    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        parsed = 3600

    return max(parsed, 1)


DEFAULT_FLEET_SUMMARY_TTL_SECONDS = _get_default_fleet_summary_ttl_seconds()

# Filesystem cache directory for behaviour summaries (`{sha256}.json`).
DRIVER_BEHAVIOUR_CACHE_DIR = Path("cache/driver_behaviour")
SHA256_HEX_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def load_event_collection_cache() -> dict[str, Any]:
    """Load event collection summary cache from the disk if it exists."""

    if EVENT_COLLECTION_CACHE_FILE.exists():
        with open(EVENT_COLLECTION_CACHE_FILE, "r") as f:
            cache: Any = json.load(f)

        return cache if isinstance(cache, dict) else {}

    return {}


def save_event_collection_cache(cache: dict[str, Any]) -> None:
    """Persist event collection summary cache dictionary to disk."""

    EVENT_COLLECTION_CACHE_FILE.parent.mkdir(exist_ok=True)

    with open(EVENT_COLLECTION_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def get_cached_summary(cache: dict[str, Any], journey_id: int) -> str | None:
    """Return a cached summary if available."""

    # JSON object keys are strings, so normalize integer ids before lookup.
    s_journey_id = str(journey_id)

    cache_entry = cache.get(s_journey_id)

    if isinstance(cache_entry, dict):
        summary = cache_entry.get("summary")

        if isinstance(summary, str):
            return summary

    return None


def store_summary(cache: dict[str, Any], journey_id: int, driver_name: str, summary: str) -> None:
    """Store a new summary in the cache."""

    # Keep cache key format aligned with `get_cached_summary` lookups.
    s_journey_id = str(journey_id)

    cache[s_journey_id] = {"driver": driver_name, "summary": summary, "generated_at": str(date.today())}


def build_driver_behaviour_cache_key(hash_source: dict[str, Any]) -> str:
    """Return deterministic SHA256 key for normalized behaviour summary payloads."""

    serialized_source = json.dumps(hash_source, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized_source.encode("utf-8")).hexdigest()


def build_fleet_summary_cache_key(collection_scope: str, normalized_data: list[dict[str, Any]]) -> str:
    """Build deterministic fleet-summary cache key with stable prefix."""

    hash_source = {
        "version": CACHE_SCHEMA_VERSION,
        "collection_scope": collection_scope,
        "data": normalized_data,
    }
    digest = build_driver_behaviour_cache_key(hash_source)
    return f"{FLEET_SUMMARY_CACHE_PREFIX}:{digest}"


def _validate_fleet_summary_cache_key(cache_key: str) -> str:
    """Validate fleet-summary cache key format and return digest part."""

    if not isinstance(cache_key, str):
        raise ValueError("Invalid cache_key: expected string")

    prefix = f"{FLEET_SUMMARY_CACHE_PREFIX}:"

    if not cache_key.startswith(prefix):
        raise ValueError("Invalid cache_key: expected fleet_summary:{sha256}")

    digest = cache_key[len(prefix) :]

    if not SHA256_HEX_PATTERN.fullmatch(digest):
        raise ValueError("Invalid cache_key digest: expected 64-char SHA256 hex")

    return digest


def _resolve_fleet_summary_ttl_seconds(ttl: int | None) -> int:
    """Return resolved fleet-summary TTL in seconds."""

    if ttl is None:
        return DEFAULT_FLEET_SUMMARY_TTL_SECONDS

    resolved_ttl = int(ttl)

    if resolved_ttl <= 0:
        raise ValueError("Invalid ttl: expected positive integer seconds")

    return resolved_ttl


def _parse_iso_utc_datetime(value: Any) -> datetime | None:
    """Parse ISO UTC timestamp string, returning None when invalid."""

    if not isinstance(value, str) or not value.strip():
        return None

    normalized_value = value.strip().replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(normalized_value)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def get_fleet_summary_cache(cache_key: str, ttl: int | None = None) -> dict[str, Any] | None:
    """Return fleet summary cache entry when present and not expired."""

    _validate_fleet_summary_cache_key(cache_key)
    ttl_seconds = _resolve_fleet_summary_ttl_seconds(ttl)

    cache = load_event_collection_cache()
    cache_entry = cache.get(cache_key)

    if not isinstance(cache_entry, dict):
        return None

    generated_at = _parse_iso_utc_datetime(cache_entry.get("generated_at"))

    if generated_at is None:
        return None

    if datetime.now(timezone.utc) - generated_at > timedelta(seconds=ttl_seconds):
        return None

    return cache_entry


def set_fleet_summary_cache(cache_key: str, value: dict[str, Any], ttl: int | None = None) -> dict[str, Any]:
    """Persist fleet summary cache entry and return stored metadata payload."""

    _validate_fleet_summary_cache_key(cache_key)
    _resolve_fleet_summary_ttl_seconds(ttl)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cache_entry = dict(value)
    cache_entry["cache_key"] = cache_key
    cache_entry["generated_at"] = generated_at

    cache = load_event_collection_cache()
    cache[cache_key] = cache_entry
    save_event_collection_cache(cache)

    return cache_entry


def _driver_behaviour_cache_file(cache_key: str) -> Path:
    """Return cache file path for a behaviour summary cache key."""

    if not SHA256_HEX_PATTERN.fullmatch(cache_key):
        raise ValueError("Invalid cache_key: expected 64-char SHA256 hex digest")

    return DRIVER_BEHAVIOUR_CACHE_DIR / f"{cache_key}.json"


def load_driver_behaviour_cache_entry(cache_key: str) -> dict[str, Any] | None:
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

    # make sure the cache entry is valid and for the correct schema version
    if entry.get("cache_version") != CACHE_SCHEMA_VERSION:
        return None

    return entry


def store_driver_behaviour_cache_entry(cache_key: str, entry: dict[str, Any]) -> None:
    """Store a behaviour summary cache entry as `cache/driver_behaviour/{sha256}.json`."""

    DRIVER_BEHAVIOUR_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _driver_behaviour_cache_file(cache_key)
    cache_entry = dict(entry)
    cache_entry["cache_version"] = CACHE_SCHEMA_VERSION

    with open(cache_file, "w") as file:
        json.dump(cache_entry, file, indent=2, sort_keys=True)
