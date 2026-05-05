"""Pipeline orchestration for CLI and API summary generation flows."""

from models.driver_summary import DriverSummary, DriverCollectionSummary
from util.data_loader import load_events
from services.driver_metrics import extract_driver_metrics
from services.summary_service import get_driver_summary
from services.ai_summary import generate_collection_summary
from cache.cache_worker import (
    load_cache,
    save_cache,
    load_event_collection_cache,
    save_event_collection_cache,
    get_cached_event_collection_summary,
    store_event_collection_summary,
)
from fastapi import HTTPException


def generate_summaries(events_file):
    """
    Generate summaries for drivers based on events data.

    :param events_file: Path to the events JSON file.
    :return: List of driver summaries.
    """

    events = load_events(events_file)

    driver_metrics = [
        extract_driver_metrics(driver)
        for driver in events
    ]

    cache = load_cache()

    summaries = []

    for driver in driver_metrics:

        summary = get_driver_summary(cache, driver)

        summaries.append(DriverSummary(
            journey_id=driver.id,
            driver=driver.name,
            summary=summary
        ))

    save_cache(cache)

    return summaries


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

def generate_single_summary(events_file, journey_id):
    """
    Generate a summary for a single journey based on the provided events file and journey ID.

    This function processes events data to extract and compute a summary for a specific driver
    and journey identified by the given journey ID. It interacts with cached records to generate
    the driver summary and updates the cache with the results.

    :param events_file: Path to the file containing event data. The data is expected to be in a
                        format that `load_events` can process.
    :type events_file: str
    :param journey_id: Unique identifier of the journey for which the summary is generated.
    :type journey_id: int
    :return: If successful, returns a dictionary containing the journey ID, driver's name, and
             the generated summary. If the journey ID is not found, returns an error dictionary
             indicating that the journey was not found.
    :rtype: dict
    """

    events = load_events(events_file)
    cache = load_cache()

    for event in events:

        if event["id"] == journey_id:

            driver = extract_driver_metrics(event)

            summary = get_driver_summary(cache, driver)

            save_cache(cache)

            return DriverSummary(
                journey_id=driver.id,
                driver=driver.name,
                summary=summary
            )

    raise HTTPException(status_code=404, detail="Journey not found")