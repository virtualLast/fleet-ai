"""Pipeline orchestration for CLI and API summary generation flows."""

from models.driver_summary import DriverSummary, DriverCollectionSummary
from services.driver_metrics import extract_driver_metrics
from services.ai_summary import generate_collection_summary, generate_driver_journey_collection_summary
from cache.cache_worker import (
    load_cache,
    save_cache,
    get_cached_summary,
    store_summary,
    load_event_collection_cache,
    save_event_collection_cache,
    get_cached_event_collection_summary,
    store_event_collection_summary,
)
from fastapi import HTTPException


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


def generate_event_collection_summary(collection_scope: str, data: list[dict]) -> DriverCollectionSummary:
    """Return one collection summary using scope-keyed cache and AI on misses."""

    normalized_data = _normalize_collection_data(data)
    driver_ids = [row["driver_id"] for row in normalized_data]
    cache = load_event_collection_cache()
    cached_summary = get_cached_event_collection_summary(cache, collection_scope)

    if cached_summary:
        return DriverCollectionSummary(**cached_summary)

    summary = generate_collection_summary(normalized_data)

    store_event_collection_summary(cache, collection_scope, driver_ids, summary)
    save_event_collection_cache(cache)

    return DriverCollectionSummary(**cache[collection_scope])


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


def generate_single_summary(journey_id, fallback_payload: dict | None = None):
    """
    Generate a summary for a single journey based on the provided events file and journey ID.

    This function processes events data to extract and compute a summary for a specific driver
    and journey identified by the given journey ID. It interacts with cached records to generate
    the driver summary and updates the cache with the results.

    :param journey_id: Unique identifier of the journey for which the summary is generated.
    :type journey_id: int
    :param fallback_payload: Optional payload context used when file lookup misses. Must include
                             `collection_scope` and `data`.
    :type fallback_payload: dict | None
    :return: If successful, returns a dictionary containing the journey ID, driver's name, and
             the generated summary. If the journey ID is not found, returns an error dictionary
             indicating that the journey was not found.
    :rtype: dict
    """

    cache = load_cache()

    if fallback_payload is not None:
        _collection_scope, data = _validate_fallback_payload(fallback_payload)
        driver_name = _extract_collection_driver_name(journey_id, data)

        cached_summary = get_cached_summary(cache, journey_id)

        if cached_summary:
            return DriverSummary(
                journey_id=journey_id,
                driver=driver_name,
                summary=cached_summary,
            )

        summary = generate_driver_journey_collection_summary(data)

        store_summary(cache, journey_id, driver_name, summary)
        save_cache(cache)

        return DriverSummary(
            journey_id=journey_id,
            driver=driver_name,
            summary=summary,
        )

    cached_summary = get_cached_summary(cache, journey_id)

    if cached_summary:
        cached_entry = cache[str(journey_id)]

        return DriverSummary(
            journey_id=journey_id,
            driver=cached_entry.get("driver", "unknown"),
            summary=cached_summary,
        )

    raise HTTPException(status_code=404, detail="Journey summary not found")