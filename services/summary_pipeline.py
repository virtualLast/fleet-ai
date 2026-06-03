"""Pipeline orchestration for CLI and API summary generation flows."""

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from cache.cache_worker import (
    CACHE_SCHEMA_VERSION,
    build_driver_behaviour_cache_key,
    build_fleet_summary_cache_key,
    get_fleet_summary_cache,
    load_driver_behaviour_cache_entry,
    set_fleet_summary_cache,
    store_driver_behaviour_cache_entry,
)
from models.driver_summary import DriverBehaviourSummary, FleetSummary
from services.ai_summary import generate_driver_behaviour_aggregated_summary, generate_fleet_summary_text
from services.risk.driver_risk_engine import DriverRiskEngine
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

    expected_driver_id: int | None = None

    for index, row in enumerate(data):
        if not isinstance(row, dict):
            raise HTTPException(status_code=400, detail=f"Invalid row at index {index}")

        raw_driver_id = row.get("driverId")

        if raw_driver_id is None:
            raise HTTPException(status_code=400, detail=f"Invalid driverId at row {index}")

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

    if expected_driver_id is None:
        raise HTTPException(status_code=400, detail="Missing required field: data")

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


def _build_driver_event_breakdown(normalized_data: list[dict]) -> dict[str, int]:
    """Build deterministic single-driver event breakdown from normalized journey rows."""

    return {
        "seatbelt": sum(max(0, int(row.get("dsmSeatbeltCount", 0) or 0)) for row in normalized_data),
        "fatigue": sum(max(0, int(row.get("dsmFatigueCount", 0) or 0)) for row in normalized_data),
        "distraction": sum(max(0, int(row.get("dsmDistractionCount", 0) or 0)) for row in normalized_data),
        "adas": sum(max(0, int(row.get("adasEventsCount", 0) or 0)) for row in normalized_data),
    }


def _build_driver_assessment_confidence(
    journey_count: int, event_breakdown: dict[str, int], normalized_data: list[dict]
) -> dict:
    """Derive deterministic assessment confidence structure for single-driver analysis payload."""

    non_zero_categories = sum(1 for value in event_breakdown.values() if value > 0)
    event_count = sum(event_breakdown.values())
    unique_days = {
        str(row.get("startTime", "")).split("T")[0]
        for row in normalized_data
        if isinstance(row.get("startTime"), str) and "T" in str(row.get("startTime"))
    }
    observation_window_days = max(len(unique_days), 1 if journey_count > 0 else 0)

    reasons = []

    if journey_count < 8:
        reasons.append("low_journey_volume")
    if non_zero_categories <= 1 and event_count > 0:
        reasons.append("limited_event_diversity")
    if observation_window_days < 7 and journey_count > 0:
        reasons.append("narrow_observation_window")

    level = "high"

    if reasons:
        level = "low" if len(reasons) >= 2 else "medium"

    return {
        "level": level,
        "derived_from": {
            "journey_volume": "low" if journey_count < 8 else "high",
            "event_diversity": "limited" if non_zero_categories <= 1 else "broad",
            "observation_window_days": observation_window_days,
            "event_volume": "low" if event_count < 12 else "high",
        },
        "reasons": reasons,
    }


def _build_driver_analysis_payload(raw_data: list[dict], normalized_data: list[dict]) -> dict:
    """Build canonical deterministic single-driver analysis payload from normalized rows."""

    risk_profile = DriverRiskEngine.build_risk_profile(normalized_data)
    journey_count = len(normalized_data)
    event_breakdown = _build_driver_event_breakdown(normalized_data)
    event_count = sum(event_breakdown.values())

    dominant_behaviours = [
        behaviour
        for behaviour, value in sorted(event_breakdown.items(), key=lambda item: (-item[1], item[0]))
        if value > 0
    ]

    behaviour_to_focus = {
        "seatbelt": "seatbelt_use",
        "fatigue": "fatigue_management",
        "distraction": "distraction_reduction",
        "adas": "adas_response_consistency",
    }
    coaching_focus = [behaviour_to_focus.get(behaviour, behaviour) for behaviour in dominant_behaviours[:2]]
    dimensions = risk_profile.get("dimensions", {}) if isinstance(risk_profile, dict) else {}
    persistent_score = float((dimensions.get("persistent", {}) or {}).get("score", 0.0) or 0.0)
    acute_score = float((dimensions.get("acute", {}) or {}).get("score", 0.0) or 0.0)
    primary_risk_dimension = "persistent" if persistent_score >= acute_score else "acute"

    return {
        "driver_name": _extract_driver_name_from_behaviour_rows(raw_data),
        "driver_id": normalized_data[0].get("driverId", 0) if normalized_data else 0,
        "analysis": {
            "journey_count": journey_count,
            "event_count": event_count,
            "event_breakdown": event_breakdown,
            "risk": {
                "score": float(risk_profile.get("risk_score", 0.0) or 0.0),
                "band": str(risk_profile.get("risk_level", "low") or "low"),
            },
            "assessment_confidence": _build_driver_assessment_confidence(
                journey_count, event_breakdown, normalized_data
            ),
            "dominant_behaviours": dominant_behaviours,
            "primary_risk_dimension": primary_risk_dimension,
            "coaching_focus": coaching_focus,
        },
    }


def _aggregate_driver_behaviour_payload(raw_data: list[dict], normalized_data: list[dict]) -> dict:
    """Build deterministic driver analysis payload plus legacy compatibility fields.

    Args:
        raw_data: Original request rows used for stable driver display-name extraction.
        normalized_data: Deterministically normalized rows used for risk analysis.

    Returns:
        A dictionary containing:
        - Legacy fields (`driver_name`, `driver_id`, `journey_count`, `event_count`,
          `risk_profile`, `behaviour_summary`) for existing summary generation flows.
        - Canonical `analysis` payload used as deterministic truth for cache contracts.
    """

    analysis_payload = _build_driver_analysis_payload(raw_data, normalized_data)
    analysis = analysis_payload["analysis"]
    risk_profile = DriverRiskEngine.build_risk_profile(normalized_data)

    behaviour_summary = {
        "seatbelt_events": int(analysis.get("event_breakdown", {}).get("seatbelt", 0) or 0),
        "fatigue_events": int(analysis.get("event_breakdown", {}).get("fatigue", 0) or 0),
        "distraction_events": int(analysis.get("event_breakdown", {}).get("distraction", 0) or 0),
        "adas_events": int(analysis.get("event_breakdown", {}).get("adas", 0) or 0),
    }

    return {
        "driver_name": analysis_payload["driver_name"],
        "driver_id": analysis_payload["driver_id"],
        "journey_count": analysis["journey_count"],
        "event_count": analysis["event_count"],
        "risk_profile": risk_profile,
        "behaviour_summary": behaviour_summary,
        "analysis": analysis,
    }


def _build_zero_event_driver_behaviour_summary(aggregated_payload: dict) -> str:
    """Build deterministic static response for all-zero behaviour event collections."""

    driver_name = aggregated_payload.get("driver_name", "unknown")
    journey_count = aggregated_payload.get("journey_count", 0)
    analysis = aggregated_payload.get("analysis", {})
    risk_level = analysis.get("risk", {}).get("band", "low")
    assessment_confidence = analysis.get("assessment_confidence", {}).get("level", "low")

    return (
        f"{driver_name} completed {journey_count} journeys with no tracked ADAS or DSM events. "
        f"The deterministic risk engine assessed overall risk as {risk_level} "
        f"with {assessment_confidence} assessment confidence. "
        "Continue routine monitoring to maintain this standard."
    )


def generate_driver_behaviour_summary(collection_scope: str, data: list[dict]) -> DriverBehaviourSummary:
    """Generate driver behaviour summary with deterministic hash-based filesystem caching."""

    # extract driver id and error if missing
    # normalise data + make a cache key
    driver_id = _validate_driver_behaviour_payload(collection_scope, data)
    normalized_data = _normalize_driver_behaviour_hash_data(data)
    cache_key = _build_driver_behaviour_cache_key(collection_scope, data)

    # try and find a cache entry
    # if one is not found, build the cache data, save and return the cache entry data
    cached_entry = load_driver_behaviour_cache_entry(cache_key)

    if cached_entry:
        summary_payload = cached_entry.get("summary", {})

        if isinstance(summary_payload, dict):
            summary_text = summary_payload.get("text", "No summary available.")
        else:
            summary_text = summary_payload or "No summary available."

        metadata = cached_entry.get("metadata", {})
        analysis = cached_entry.get("analysis", {})
        cached_driver_id = analysis.get(
            "driver_id", metadata.get("driver_id", cached_entry.get("driver_id", driver_id))
        )
        cached_event_count = analysis.get("event_count", cached_entry.get("event_count", 0))

        return DriverBehaviourSummary(
            cached=True,
            cache_key=cache_key,
            driver_id=cached_driver_id,
            event_count=cached_event_count,
            summary=summary_text,
        )

    aggregated_payload = _aggregate_driver_behaviour_payload(data, normalized_data)

    if aggregated_payload["event_count"] <= 0:
        summary = _build_zero_event_driver_behaviour_summary(aggregated_payload)
    else:
        summary = generate_driver_behaviour_aggregated_summary(aggregated_payload)

    cache_entry = {
        "cache_version": CACHE_SCHEMA_VERSION,
        "metadata": {
            "cache_key": cache_key,
            "cache_version": CACHE_SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "model": "gpt-5.4",
            "driver_id": aggregated_payload["driver_id"],
        },
        "analysis": {
            "driver_id": aggregated_payload["driver_id"],
            **aggregated_payload["analysis"],
        },
        "summary": summary,
        "summary_payload": {"text": summary},
        "driver_id": aggregated_payload["driver_id"],
        "event_count": aggregated_payload["event_count"],
    }
    store_driver_behaviour_cache_entry(cache_key, cache_entry)

    return DriverBehaviourSummary(
        cached=False,
        cache_key=cache_key,
        driver_id=int(cache_entry["driver_id"]),
        event_count=int(cache_entry["event_count"]),
        summary=summary,
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
        cached_summary = cached_entry.get("summary", {})
        summary_text = (
            cached_summary.get("text", "No summary available.")
            if isinstance(cached_summary, dict)
            else str(cached_summary)
        )
        metadata = cached_entry.get("metadata", {}) if isinstance(cached_entry.get("metadata", {}), dict) else {}
        generated_at = str(metadata.get("generated_at", cached_entry.get("generated_at", "")) or "")

        return FleetSummary(
            summary=summary_text,
            generated_at=generated_at,
            cache_hit=True,
        )

    event_breakdown = {
        "seatbelt": sum(max(0, int(row.get("dsmSeatbeltCount", 0) or 0)) for row in normalized_data),
        "handheld_device": sum(max(0, int(row.get("dsmHandheldDevicesCount", 0) or 0)) for row in normalized_data),
        "distraction": sum(max(0, int(row.get("dsmDistractionCount", 0) or 0)) for row in normalized_data),
        "smoking": sum(max(0, int(row.get("dsmSmokingCount", 0) or 0)) for row in normalized_data),
        "fatigue": sum(max(0, int(row.get("dsmFatigueCount", 0) or 0)) for row in normalized_data),
        "adas": sum(max(0, int(row.get("adasEventsCount", 0) or 0)) for row in normalized_data),
    }

    fleet_analysis = {
        "driver_count": len({int(row.get("id", 0) or 0) for row in normalized_data}),
        "event_count": sum(event_breakdown.values()),
        "event_breakdown": event_breakdown,
        "top_drivers": [
            {
                "driver_id": int(row.get("id", 0) or 0),
                "name": str(row.get("entityName", "unknown") or "unknown"),
                "event_count": int(row.get("adasEventsCount", 0) or 0) + int(row.get("dsmEventsCount", 0) or 0),
                "primary_behaviour": "seatbelt",
            }
            for row in sorted(
                normalized_data,
                key=lambda item: (
                    -(int(item.get("adasEventsCount", 0) or 0) + int(item.get("dsmEventsCount", 0) or 0)),
                    str(item.get("entityName", "")),
                ),
            )[:3]
            if (int(row.get("adasEventsCount", 0) or 0) + int(row.get("dsmEventsCount", 0) or 0)) > 0
        ],
        "site_clusters": sorted(
            {
                str(row.get("fleetLevelName", "unknown") or "unknown")
                for row in normalized_data
                if str(row.get("fleetLevelName", "")).strip()
            }
        ),
        "dominant_risk_theme": "seatbelt_non_compliance"
        if event_breakdown["seatbelt"] >= event_breakdown["handheld_device"]
        else "mobile_phone_distraction",
        "risk_distribution": "outlier_concentrated",
        "anomalies": ["no_adas_events_detected"] if event_breakdown["adas"] == 0 else [],
        "recommended_actions": ["seatbelt_coaching", "targeted_mobile_phone_intervention"],
        "assessment_confidence": {
            "level": "high" if len(normalized_data) >= 15 else "medium",
            "derived_from": {
                "driver_volume": "high" if len(normalized_data) >= 15 else "low",
                "event_volume": "high" if sum(event_breakdown.values()) >= 50 else "low",
                "behavioural_distribution": "broad"
                if sum(1 for value in event_breakdown.values() if value > 0) >= 3
                else "limited",
            },
            "reasons": [],
        },
    }

    summary = generate_fleet_summary_text(normalized_data)
    cache_entry = set_fleet_summary_cache(
        cache_key,
        {
            "metadata": {
                "cache_key": cache_key,
                "cache_version": CACHE_SCHEMA_VERSION,
                "model": "gpt-5.4",
            },
            "analysis": fleet_analysis,
            "summary_payload": {"text": summary},
            "summary": summary,
        },
    )

    response_summary = cache_entry.get("summary", {})
    if isinstance(response_summary, dict):
        response_summary_text = response_summary.get("text", "No summary available.")
    else:
        response_summary_text = str(response_summary or "No summary available.")

    return FleetSummary(
        summary=response_summary_text,
        generated_at=str(
            (cache_entry.get("metadata", {}) if isinstance(cache_entry.get("metadata", {}), dict) else {}).get(
                "generated_at", cache_entry.get("generated_at", "")
            )
            or ""
        ),
        cache_hit=False,
    )


def _normalize_collection_data(raw_data: list[dict]) -> list[dict]:
    """Normalize raw collection rows into prompt-ready dictionaries.

    Key behavior:
    - Coerce numeric fields to integers with safe fallbacks.
    - Produce stable unique `driver_id` values even with missing/duplicate ids.
    - Keep `fleet_name`/`driver_name` labels for AI summary context.
    """

    def _safe_int(value: Any, fallback: int | None = 0) -> int | None:
        """Convert `value` to int and return `fallback` when conversion fails."""
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

        normalized_data.append(
            {
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
            }
        )

    return normalized_data
