"""Pipeline orchestration for CLI and API summary generation flows."""

from datetime import datetime
from datetime import timezone

from models.driver_summary import DriverBehaviourSummary, FleetSummary
from services.driver_metrics import extract_driver_metrics
from services.ai_summary import (
    generate_driver_behaviour_aggregated_summary,
    generate_fleet_summary_text,
)
from services.risk.driver_risk_engine import DriverRiskEngine
from cache.cache_worker import (
    CACHE_SCHEMA_VERSION,
    build_driver_behaviour_cache_key,
    load_driver_behaviour_cache_entry,
    store_driver_behaviour_cache_entry,
    build_fleet_summary_cache_key,
    get_fleet_summary_cache,
    set_fleet_summary_cache,
)
from fastapi import HTTPException
from util.summary_normalization import normalize_summary_dataset


DRIVER_BEHAVIOUR_HASH_FIELDS = (
    "adasFcwCount",
    "adasHmwCount",
    "adasPcwCount",
    "adasEventsCount",
    "dsmFatigueCount",
    "dsmNoDriverCount",
    "dsmHandheldDevicesCount",
    "dsmSmokingCount",
    "dsmDistractionCount",
    "dsmYawningCount",
    "dsmSeatbeltCount",
    "dsmEventsCount",
)

FLEET_SUMMARY_INT_FIELDS = (
    "id",
    "fleetLevelId",
    *DRIVER_BEHAVIOUR_HASH_FIELDS,
)

FLEET_SUMMARY_TEXT_FIELDS = (
    "fleetLevelName",
    "entityName",
    "vrn",
)


def _normalize_driver_behaviour_hash_data(raw_data: list[dict]) -> list[dict]:
    """Return deterministic hash-ready rows for behaviour summary caching.

    Normalization rules:
    - Keep only stable fields relevant to caching semantics.
    - Coerce numeric event counters and identifiers into integers.
    - Exclude non-deterministic / irrelevant fields (e.g. positions, addresses).
    - Sort by stable keys so payload ordering does not change cache keys.
    """

    return normalize_summary_dataset(
        raw_data,
        int_fields=("id", "driverId", *DRIVER_BEHAVIOUR_HASH_FIELDS),
        text_fields=("startTime", "endTime"),
        sort_keys=("id", "driverId", "startTime", "endTime"),
    )


def _build_driver_behaviour_hash_source(collection_scope: str, raw_data: list[dict]) -> dict:
    """Build deterministic hash source for behaviour summary cache key generation."""

    return {
        "version": CACHE_SCHEMA_VERSION,
        "collection_scope": collection_scope,
        "data": _normalize_driver_behaviour_hash_data(raw_data),
    }


def _build_driver_behaviour_cache_key(collection_scope: str, raw_data: list[dict]) -> str:
    """Generate deterministic SHA256 cache key for behaviour summary requests."""

    hash_source = _build_driver_behaviour_hash_source(collection_scope, raw_data)
    return build_driver_behaviour_cache_key(hash_source)


def _validate_driver_behaviour_payload(collection_scope: str, data: list[dict]) -> int:
    """Validate behaviour payload semantics and return the single driver id."""

    if not isinstance(collection_scope, str) or not collection_scope.strip():
        raise HTTPException(status_code=400, detail="Missing required field: collection_scope")

    if not isinstance(data, list) or not data:
        raise HTTPException(status_code=400, detail="Missing required field: data")

    expected_driver_id = None

    for index, row in enumerate(data):
        if not isinstance(row, dict):
            raise HTTPException(status_code=400, detail=f"Invalid row at index {index}")

        raw_driver_id = row.get("driverId")

        try:
            driver_id = int(raw_driver_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"Invalid driverId at row {index}")

        if driver_id <= 0:
            raise HTTPException(status_code=400, detail=f"Invalid driverId at row {index}")

        if expected_driver_id is None:
            expected_driver_id = driver_id
        elif driver_id != expected_driver_id:
            raise HTTPException(status_code=400, detail="Payload must contain exactly one driverId")

        for timestamp_field in ("startTime", "endTime"):
            raw_timestamp = row.get(timestamp_field)

            if not isinstance(raw_timestamp, str) or not raw_timestamp.strip():
                raise HTTPException(status_code=400, detail=f"Malformed timestamp: {timestamp_field}")

            normalized_timestamp = raw_timestamp.strip().replace("Z", "+00:00")

            try:
                datetime.fromisoformat(normalized_timestamp)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Malformed timestamp: {timestamp_field}")

    return expected_driver_id


def _extract_driver_name_from_behaviour_rows(raw_data: list[dict]) -> str:
    """Return the first non-empty driver name available in behaviour payload rows."""

    for row in raw_data:
        if not isinstance(row, dict):
            continue

        raw_name = row.get("entityName")

        if isinstance(raw_name, str) and raw_name.strip():
            return raw_name.strip()

    return "unknown"


def _calculate_behaviour_row_event_count(row: dict) -> int:
    """Return per-journey tracked event total used for response metadata."""

    return max(0, int(row.get("adasEventsCount", 0) or 0)) + max(0, int(row.get("dsmEventsCount", 0) or 0))


def _build_behaviour_summary_from_breakdown(behaviour_breakdown: dict) -> dict:
    """Build AI-facing behaviour summary counters from risk-engine breakdown."""

    return {
        "seatbelt_events": int(behaviour_breakdown.get("dsm_seatbelt", {}).get("raw_event_count", 0) or 0),
        "fatigue_events": int(behaviour_breakdown.get("dsm_fatigue", {}).get("raw_event_count", 0) or 0),
        "distraction_events": int(behaviour_breakdown.get("dsm_distraction", {}).get("raw_event_count", 0) or 0),
        "adas_events": int(behaviour_breakdown.get("adas_events", {}).get("raw_event_count", 0) or 0),
    }


def _aggregate_driver_behaviour_payload(raw_data: list[dict], normalized_data: list[dict]) -> dict:
    """Build strict AI payload from deterministic risk-engine outputs."""

    risk_profile = DriverRiskEngine.build_risk_profile(normalized_data)
    behaviour_breakdown = DriverRiskEngine.compute_behaviour_breakdown(normalized_data)
    behaviour_summary = _build_behaviour_summary_from_breakdown(behaviour_breakdown)

    if not normalized_data:
        return {
            "driver_name": _extract_driver_name_from_behaviour_rows(raw_data),
            "driver_id": 0,
            "journey_count": 0,
            "event_count": 0,
            "risk_profile": risk_profile,
            "behaviour_summary": behaviour_summary,
        }

    driver_id = normalized_data[0].get("driverId", 0)
    event_count = sum(_calculate_behaviour_row_event_count(row) for row in normalized_data)

    return {
        "driver_name": _extract_driver_name_from_behaviour_rows(raw_data),
        "driver_id": driver_id,
        "journey_count": len(normalized_data),
        "event_count": event_count,
        "risk_profile": risk_profile,
        "behaviour_summary": behaviour_summary,
    }


def _build_zero_event_driver_behaviour_summary(aggregated_payload: dict) -> str:
    """Build deterministic static response for all-zero behaviour event collections."""

    driver_name = aggregated_payload.get("driver_name", "unknown")
    journey_count = aggregated_payload.get("journey_count", 0)
    risk_profile = aggregated_payload.get("risk_profile", {})
    risk_level = risk_profile.get("risk_level", "low")
    confidence = risk_profile.get("confidence", "low")

    return (
        f"{driver_name} completed {journey_count} journeys with no tracked ADAS or DSM events. "
        f"The deterministic risk engine assessed overall risk as {risk_level} with {confidence} confidence. "
        "Continue routine monitoring to maintain this standard."
    )


def generate_driver_behaviour_summary(collection_scope: str, data: list[dict]) -> DriverBehaviourSummary:
    """Generate driver behaviour summary with deterministic hash-based filesystem caching."""

    driver_id = _validate_driver_behaviour_payload(collection_scope, data)
    normalized_data = _normalize_driver_behaviour_hash_data(data)
    cache_key = _build_driver_behaviour_cache_key(collection_scope, data)

    cached_entry = load_driver_behaviour_cache_entry(cache_key)

    if cached_entry:
        return DriverBehaviourSummary(
            cached=True,
            cache_key=cache_key,
            driver_id=cached_entry.get("driver_id", driver_id),
            event_count=cached_entry.get("event_count", 0),
            summary=cached_entry.get("summary", "No summary available."),
        )

    aggregated_payload = _aggregate_driver_behaviour_payload(data, normalized_data)

    if aggregated_payload["event_count"] <= 0:
        summary = _build_zero_event_driver_behaviour_summary(aggregated_payload)
    else:
        summary = generate_driver_behaviour_aggregated_summary(aggregated_payload)

    cache_entry = {
        "cache_key": cache_key,
        "cache_version": CACHE_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "driver_id": aggregated_payload["driver_id"],
        "event_count": aggregated_payload["event_count"],
        "summary": summary,
    }
    store_driver_behaviour_cache_entry(cache_key, cache_entry)

    return DriverBehaviourSummary(
        cached=False,
        cache_key=cache_key,
        driver_id=cache_entry["driver_id"],
        event_count=cache_entry["event_count"],
        summary=cache_entry["summary"],
    )


def generate_fleet_summary(collection_scope: str, data: list[dict]) -> FleetSummary:
    """Generate aggregate fleet-level summary using cache-first orchestration."""

    if not isinstance(collection_scope, str) or not collection_scope.strip():
        raise HTTPException(status_code=400, detail="Missing required field: collection_scope")

    if not isinstance(data, list) or not data:
        raise HTTPException(status_code=400, detail="Missing required field: data")

    normalized_data = normalize_summary_dataset(
        data,
        int_fields=FLEET_SUMMARY_INT_FIELDS,
        text_fields=FLEET_SUMMARY_TEXT_FIELDS,
        text_defaults={
            "fleetLevelName": "unknown",
            "entityName": "unknown",
            "vrn": "",
        },
        sort_keys=("id", "fleetLevelId", "entityName"),
    )
    cache_key = build_fleet_summary_cache_key(collection_scope.strip(), normalized_data)
    cached_entry = get_fleet_summary_cache(cache_key)

    if cached_entry:
        return FleetSummary(
            summary=cached_entry.get("summary", "No summary available."),
            generated_at=cached_entry.get("generated_at", ""),
            cache_hit=True,
        )

    summary = generate_fleet_summary_text(normalized_data)
    cache_entry = set_fleet_summary_cache(cache_key, {"summary": summary})

    return FleetSummary(
        summary=cache_entry.get("summary", "No summary available."),
        generated_at=cache_entry.get("generated_at", ""),
        cache_hit=False,
    )


def _normalize_collection_data(raw_data: list[dict]) -> list[dict]:
    """Normalize raw collection rows into prompt-ready dictionaries.

    Key behavior:
    - Coerce numeric fields to integers with safe fallbacks.
    - Produce stable unique `driver_id` values even with missing/duplicate ids.
    - Keep `fleet_name`/`driver_name` labels for AI summary context.
    """

    def _safe_int(value, fallback=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    normalized_data = []
    used_driver_ids = set()

    for index, row in enumerate(raw_data):
        raw_driver_id = row.get("id")

        if raw_driver_id is None:
            raw_driver_id = row.get("fleetLevelId")

        driver_id = _safe_int(raw_driver_id, None)

        if driver_id is None or driver_id in used_driver_ids:
            driver_id = index

            while driver_id in used_driver_ids:
                driver_id += len(raw_data) or 1

        used_driver_ids.add(driver_id)

        normalized_data.append({
            "driver_id": driver_id,
            "driver_name": row.get("entityName", "unknown"),
            "fleet_name": row.get("fleetLevelName", "unknown"),
            "adasFcwCount": _safe_int(row.get("adasFcwCount", 0) or 0),
            "adasHmwCount": _safe_int(row.get("adasHmwCount", 0) or 0),
            "adasPcwCount": _safe_int(row.get("adasPcwCount", 0) or 0),
            "adasEventsCount": _safe_int(row.get("adasEventsCount", 0) or 0),
            "dsmFatigueCount": _safe_int(row.get("dsmFatigueCount", 0) or 0),
            "dsmNoDriverCount": _safe_int(row.get("dsmNoDriverCount", 0) or 0),
            "dsmHandheldDevicesCount": _safe_int(row.get("dsmHandheldDevicesCount", 0) or 0),
            "dsmSmokingCount": _safe_int(row.get("dsmSmokingCount", 0) or 0),
            "dsmDistractionCount": _safe_int(row.get("dsmDistractionCount", 0) or 0),
            "dsmYawningCount": _safe_int(row.get("dsmYawningCount", 0) or 0),
            "dsmSeatbeltCount": _safe_int(row.get("dsmSeatbeltCount", 0) or 0),
            "dsmEventsCount": _safe_int(row.get("dsmEventsCount", 0) or 0),
        })

    return normalized_data


def _get_matching_fallback_row(journey_id: int, data: list[dict]) -> dict | None:
    """Return the payload row that matches journey id by `id` or `fleetLevelId`."""

    for row in data:
        raw_row_id = row.get("id")

        if raw_row_id is None:
            raw_row_id = row.get("fleetLevelId")

        try:
            row_id = int(raw_row_id)
        except (TypeError, ValueError):
            continue

        if row_id == journey_id:
            return row

    return None


def _validate_fallback_payload(fallback_payload: dict | None) -> tuple[str, list[dict]]:
    """Validate secondary endpoint fallback context and return scope + payload rows."""

    if fallback_payload is None:
        raise HTTPException(
            status_code=400,
            detail="Missing required fallback payload: collection_scope and data",
        )

    collection_scope = fallback_payload.get("collection_scope")

    if not isinstance(collection_scope, str) or not collection_scope.strip():
        raise HTTPException(status_code=400, detail="Missing required field: collection_scope")

    data = fallback_payload.get("data")

    if not isinstance(data, list) or not data:
        raise HTTPException(status_code=400, detail="Missing required field: data")

    return collection_scope.strip(), data


def _extract_collection_driver_name(journey_id: int, data: list[dict]) -> str:
    """Return a representative driver name, preferring a journey-id row match."""

    matching_row = _get_matching_fallback_row(journey_id, data)

    if matching_row is not None:
        raw_name = matching_row.get("entityName")

        if isinstance(raw_name, str) and raw_name.strip():
            return raw_name.strip()

    for row in data:
        raw_name = row.get("entityName")

        if isinstance(raw_name, str) and raw_name.strip():
            return raw_name.strip()

    return "unknown"


def _extract_fallback_driver_metrics(journey_id: int, row: dict):
    """Validate minimum fallback row fields and convert to driver metrics."""

    required_fields = ("fleetLevelName", "entityName")
    missing_fields = [field for field in required_fields if not row.get(field)]

    if missing_fields:
        missing_labels = ", ".join(missing_fields)
        raise HTTPException(status_code=400, detail=f"Missing required data fields: {missing_labels}")

    enriched_row = dict(row)
    enriched_row["id"] = journey_id

    return extract_driver_metrics(enriched_row)
