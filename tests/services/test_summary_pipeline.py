import pytest
from fastapi import HTTPException

from services import summary_pipeline


def test_normalize_collection_data_handles_id_fallback_uniqueness_and_coercion():
    """What: Normalize fleet collection rows with ID fallback and integer coercion.

    Why: Cache and aggregation paths require unique stable driver IDs and numeric counters.

    How: Provide mixed-validity rows and assert deterministic `driver_id` assignment and coerced event fields.
    """

    raw_data = [
        {
            "id": "10",
            "entityName": "Driver A",
            "fleetLevelName": "North",
            "adasFcwCount": "5",
            "dsmFatigueCount": None,
        },
        {
            "id": "10",
            "entityName": "Driver B",
            "fleetLevelName": "South",
            "adasFcwCount": "x",
            "dsmFatigueCount": "2",
        },
        {
            "fleetLevelId": "invalid",
            "entityName": "Driver C",
            "fleetLevelName": "East",
            "adasFcwCount": 1,
            "dsmFatigueCount": "bad",
        },
    ]

    normalized = summary_pipeline._normalize_collection_data(raw_data)

    assert [row["driver_id"] for row in normalized] == [10, 1, 2]
    assert len({row["driver_id"] for row in normalized}) == 3
    assert normalized[0]["adasFcwCount"] == 5
    assert normalized[1]["adasFcwCount"] == 0
    assert normalized[0]["dsmFatigueCount"] == 0
    assert normalized[1]["dsmFatigueCount"] == 2
    assert normalized[2]["dsmFatigueCount"] == 0


def test_normalize_driver_behaviour_hash_data_is_deterministic_and_whitelisted():
    """What: Normalize behaviour hash payloads into deterministic, whitelisted fields only.

    Why: Cache keys must ignore irrelevant fields and remain stable across type variants.

    How: Pass mixed typed rows with extra location fields, then assert sorted IDs, allowed keys, and value coercion.
    """

    raw_data = [
        {
            "id": "2",
            "driverId": "312870",
            "startTime": "2026-04-06T13:13:53+00:00",
            "endTime": "2026-04-06T13:21:09+00:00",
            "adasEventsCount": "0",
            "dsmEventsCount": "1",
            "dsmSeatbeltCount": "1",
            "startPosn": ["51.0", "-3.0", "Address A"],
            "endPosn": ["51.1", "-3.1", "Address B"],
        },
        {
            "id": 1,
            "driverId": 312870,
            "startTime": "2026-04-04T13:32:23+00:00",
            "endTime": "2026-04-04T13:44:43+00:00",
            "adasEventsCount": 0,
            "dsmEventsCount": "0",
            "dsmSeatbeltCount": 0,
        },
    ]

    normalized = summary_pipeline._normalize_driver_behaviour_hash_data(raw_data)

    expected_keys = {
        "id",
        "driverId",
        "startTime",
        "endTime",
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
    }

    assert [row["id"] for row in normalized] == [1, 2]
    assert all(set(row.keys()) == expected_keys for row in normalized)
    assert normalized[1]["driverId"] == 312870
    assert normalized[1]["dsmSeatbeltCount"] == 1
    assert "startPosn" not in normalized[1]
    assert "endPosn" not in normalized[1]


def test_build_driver_behaviour_cache_key_is_stable_for_order_and_type_variants():
    """What: Verify behaviour cache keys are stable across row order and scalar type differences.

    Why: Equivalent payload semantics should map to the same cache key and avoid duplicate cache entries.

    How: Build two semantically equivalent datasets with different ordering/types and compare generated keys.
    """

    data_variant_a = [
        {
            "id": 11,
            "driverId": 312870,
            "startTime": "2026-04-06T12:58:02+00:00",
            "endTime": "2026-04-06T13:10:30+00:00",
            "adasEventsCount": 0,
            "dsmEventsCount": 1,
            "dsmSeatbeltCount": 1,
        },
        {
            "id": 12,
            "driverId": 312870,
            "startTime": "2026-04-06T13:13:53+00:00",
            "endTime": "2026-04-06T13:21:09+00:00",
            "adasEventsCount": 0,
            "dsmEventsCount": 1,
            "dsmSeatbeltCount": 1,
        },
    ]

    data_variant_b = [
        {
            "id": "12",
            "driverId": "312870",
            "startTime": "2026-04-06T13:13:53+00:00",
            "endTime": "2026-04-06T13:21:09+00:00",
            "adasEventsCount": "0",
            "dsmEventsCount": "1",
            "dsmSeatbeltCount": "1",
            "startPosn": ["51.0", "-3.0", "Address"],
        },
        {
            "id": "11",
            "driverId": "312870",
            "startTime": "2026-04-06T12:58:02+00:00",
            "endTime": "2026-04-06T13:10:30+00:00",
            "adasEventsCount": "0",
            "dsmEventsCount": "1",
            "dsmSeatbeltCount": "1",
            "endPosn": ["51.1", "-3.1", "Address"],
        },
    ]

    key_a = summary_pipeline._build_driver_behaviour_cache_key("scope-a", data_variant_a)
    key_b = summary_pipeline._build_driver_behaviour_cache_key("scope-a", data_variant_b)

    assert key_a == key_b


def test_build_driver_behaviour_cache_key_changes_when_relevant_data_changes():
    """What: Verify behaviour cache keys change when meaningful payload or scope values change.

    Why: Cache isolation must invalidate entries when event counts or collection scope differ.

    How: Generate keys from baseline, changed-event, and changed-scope inputs and assert inequality.
    """

    baseline_data = [
        {
            "id": 11,
            "driverId": 312870,
            "startTime": "2026-04-06T12:58:02+00:00",
            "endTime": "2026-04-06T13:10:30+00:00",
            "adasEventsCount": 0,
            "dsmEventsCount": 1,
            "dsmSeatbeltCount": 1,
        }
    ]

    changed_data = [
        {
            "id": 11,
            "driverId": 312870,
            "startTime": "2026-04-06T12:58:02+00:00",
            "endTime": "2026-04-06T13:10:30+00:00",
            "adasEventsCount": 0,
            "dsmEventsCount": 2,
            "dsmSeatbeltCount": 1,
        }
    ]

    baseline_key = summary_pipeline._build_driver_behaviour_cache_key("scope-a", baseline_data)
    changed_key = summary_pipeline._build_driver_behaviour_cache_key("scope-a", changed_data)
    changed_scope_key = summary_pipeline._build_driver_behaviour_cache_key("scope-b", baseline_data)

    assert baseline_key != changed_key
    assert baseline_key != changed_scope_key


def test_validate_driver_behaviour_payload_rejects_missing_or_empty_data():
    """What: Reject missing or empty behaviour payload collections.

    Why: Summary generation requires at least one journey row before validation and aggregation can proceed.

    How: Call payload validation with `None` and `[]`, then assert HTTP 400 with the required error detail.
    """

    with pytest.raises(HTTPException) as missing_data_exc:
        summary_pipeline._validate_driver_behaviour_payload("scope-a", None)

    assert missing_data_exc.value.status_code == 400
    assert missing_data_exc.value.detail == "Missing required field: data"

    with pytest.raises(HTTPException) as empty_data_exc:
        summary_pipeline._validate_driver_behaviour_payload("scope-a", [])

    assert empty_data_exc.value.status_code == 400
    assert empty_data_exc.value.detail == "Missing required field: data"


def test_validate_driver_behaviour_payload_rejects_invalid_driver_id():
    """What: Reject behaviour payload rows with non-numeric driver identifiers.

    Why: The pipeline depends on a valid integer `driverId` for consistent aggregation and caching.

    How: Submit a row with invalid `driverId` text and assert an HTTP 400 `Invalid driverId` response.
    """

    with pytest.raises(HTTPException) as exc_info:
        summary_pipeline._validate_driver_behaviour_payload(
            "scope-a",
            [{"driverId": "bad", "startTime": "2026-04-06T12:58:02+00:00", "endTime": "2026-04-06T13:10:30+00:00"}],
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid driverId at row 0"


def test_validate_driver_behaviour_payload_rejects_malformed_timestamps():
    """What: Reject payload rows containing malformed timestamp fields.

    Why: Behaviour rows must carry parseable temporal bounds for valid journey semantics.

    How: Provide a row with an invalid `startTime` and assert an HTTP 400 malformed timestamp error.
    """

    with pytest.raises(HTTPException) as exc_info:
        summary_pipeline._validate_driver_behaviour_payload(
            "scope-a",
            [{"driverId": 312870, "startTime": "not-a-timestamp", "endTime": "2026-04-06T13:10:30+00:00"}],
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Malformed timestamp: startTime"


def test_validate_driver_behaviour_payload_rejects_mixed_driver_ids():
    """What: Reject payloads that mix multiple driver IDs in a single request.

    Why: Driver behaviour summaries are defined for exactly one driver identity per payload.

    How: Validate a two-row payload with different `driverId` values and assert HTTP 400 mismatch error.
    """

    with pytest.raises(HTTPException) as exc_info:
        summary_pipeline._validate_driver_behaviour_payload(
            "scope-a",
            [
                {"driverId": 312870, "startTime": "2026-04-06T12:58:02+00:00", "endTime": "2026-04-06T13:10:30+00:00"},
                {"driverId": 1, "startTime": "2026-04-06T13:13:53+00:00", "endTime": "2026-04-06T13:21:09+00:00"},
            ],
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Payload must contain exactly one driverId"


def test_aggregate_driver_behaviour_payload_returns_risk_profile_and_behaviour_summary():
    """What: Aggregate normalized behaviour rows into deterministic profile and behaviour counters.

    Why: Downstream AI narration relies on a stable aggregated payload contract.

    How: Aggregate representative rows and assert driver metadata, event totals, behaviour summary, and risk profile.
    """

    raw_data = [
        {"entityName": "David Price"},
        {"entityName": "David Price"},
    ]
    normalized_data = [
        {
            "id": 1,
            "driverId": 312870,
            "startTime": "2026-04-01T14:10:08+00:00",
            "endTime": "2026-04-01T14:37:18+00:00",
            "adasFcwCount": 0,
            "adasHmwCount": 0,
            "adasPcwCount": 0,
            "adasEventsCount": 0,
            "dsmFatigueCount": 0,
            "dsmNoDriverCount": 0,
            "dsmHandheldDevicesCount": 0,
            "dsmSmokingCount": 0,
            "dsmDistractionCount": 0,
            "dsmYawningCount": 0,
            "dsmSeatbeltCount": 1,
            "dsmEventsCount": 1,
        },
        {
            "id": 2,
            "driverId": 312870,
            "startTime": "2026-04-06T13:13:53+00:00",
            "endTime": "2026-04-06T13:21:09+00:00",
            "adasFcwCount": 0,
            "adasHmwCount": 0,
            "adasPcwCount": 0,
            "adasEventsCount": 0,
            "dsmFatigueCount": 1,
            "dsmNoDriverCount": 0,
            "dsmHandheldDevicesCount": 0,
            "dsmSmokingCount": 0,
            "dsmDistractionCount": 1,
            "dsmYawningCount": 0,
            "dsmSeatbeltCount": 0,
            "dsmEventsCount": 2,
        },
    ]

    aggregated = summary_pipeline._aggregate_driver_behaviour_payload(raw_data, normalized_data)

    assert aggregated["driver_name"] == "David Price"
    assert aggregated["driver_id"] == 312870
    assert aggregated["journey_count"] == 2
    assert aggregated["event_count"] == 3
    assert aggregated["behaviour_summary"] == {
        "seatbelt_events": 1,
        "fatigue_events": 1,
        "distraction_events": 1,
        "adas_events": 0,
    }
    assert aggregated["risk_profile"] == {
        "model_version": "v1",
        "risk_level": "high",
        "risk_score": 5.5,
        "confidence": "medium",
        "primary_concerns": ["fatigue", "distraction", "seatbelt"],
        "requires_intervention": True,
    }


def test_aggregate_driver_behaviour_payload_handles_empty_normalized_data():
    """What: Return a deterministic zero-state payload when no normalized behaviour rows exist.

    Why: The pipeline must produce a safe default contract for empty data scenarios.

    How: Aggregate empty inputs and assert default unknown driver values, low-risk profile, and zeroed counters.
    """

    aggregated = summary_pipeline._aggregate_driver_behaviour_payload([], [])

    assert aggregated == {
        "driver_name": "unknown",
        "driver_id": 0,
        "journey_count": 0,
        "event_count": 0,
        "risk_profile": {
            "model_version": "v1",
            "risk_level": "low",
            "risk_score": 0.0,
            "confidence": "low",
            "primary_concerns": [],
            "requires_intervention": False,
        },
        "behaviour_summary": {
            "seatbelt_events": 0,
            "fatigue_events": 0,
            "distraction_events": 0,
            "adas_events": 0,
        },
    }


def test_generate_driver_behaviour_summary_returns_cached_result(monkeypatch):
    """What: Short-circuit driver summary generation when a cache entry is available.

    Why: Cache hits should avoid unnecessary aggregation and AI calls while preserving response contract fields.

    How: Monkeypatch cache load to return an entry, forbid aggregation execution, and assert cached response values.
    """

    cached_entry = {
        "driver_id": 312870,
        "event_count": 7,
        "summary": "Cached behaviour summary",
    }

    monkeypatch.setattr(summary_pipeline, "load_driver_behaviour_cache_entry", lambda _cache_key: cached_entry)
    monkeypatch.setattr(
        summary_pipeline,
        "_aggregate_driver_behaviour_payload",
        lambda *_args, **_kwargs: pytest.fail("Aggregation should not run on cache hit"),
    )

    result = summary_pipeline.generate_driver_behaviour_summary(
        "scope-a",
        [
            {
                "id": 1,
                "driverId": 312870,
                "startTime": "2026-04-06T12:58:02+00:00",
                "endTime": "2026-04-06T13:10:30+00:00",
            }
        ],
    )

    assert result.cached is True
    assert result.driver_id == 312870
    assert result.event_count == 7
    assert result.summary == "Cached behaviour summary"
    assert len(result.cache_key) == 64


def test_generate_driver_behaviour_summary_generates_and_stores_on_cache_miss(monkeypatch):
    """What: Generate and persist a driver summary when no cache entry exists.

    Why: Cache misses must execute the generation path and write back a cacheable result.

    How: Stub cache read miss and AI summary output, capture store call, and assert response/cache payload contents.
    """

    stored = {}

    monkeypatch.setattr(summary_pipeline, "load_driver_behaviour_cache_entry", lambda _cache_key: None)
    monkeypatch.setattr(
        summary_pipeline,
        "generate_driver_behaviour_aggregated_summary",
        lambda _aggregated: "Generated behaviour summary",
    )

    def fake_store(cache_key, entry):
        stored["cache_key"] = cache_key
        stored["entry"] = entry

    monkeypatch.setattr(summary_pipeline, "store_driver_behaviour_cache_entry", fake_store)

    result = summary_pipeline.generate_driver_behaviour_summary(
        "scope-a",
        [
            {
                "id": 1,
                "entityName": "David Price",
                "driverId": 312870,
                "startTime": "2026-04-06T12:58:02+00:00",
                "endTime": "2026-04-06T13:10:30+00:00",
                "dsmEventsCount": 1,
                "dsmSeatbeltCount": 1,
            }
        ],
    )

    assert result.cached is False
    assert result.driver_id == 312870
    assert result.event_count == 1
    assert result.summary == "Generated behaviour summary"
    assert stored["cache_key"] == result.cache_key
    assert stored["entry"]["cache_version"] == "v1"
    assert stored["entry"]["summary"] == "Generated behaviour summary"


def test_generate_driver_behaviour_summary_zero_events_skips_ai_request(monkeypatch):
    """What: Skip AI summary generation when aggregated event count is zero.

    Why: Zero-event payloads should use deterministic fallback messaging instead of invoking AI.

    How: Force cache miss, fail fast on AI call, run generation with zero-event data, and assert fallback summary text.
    """

    monkeypatch.setattr(summary_pipeline, "load_driver_behaviour_cache_entry", lambda _cache_key: None)
    monkeypatch.setattr(
        summary_pipeline,
        "generate_driver_behaviour_aggregated_summary",
        lambda _aggregated: pytest.fail("AI summary should not run for zero-event payload"),
    )
    monkeypatch.setattr(summary_pipeline, "store_driver_behaviour_cache_entry", lambda *_args: None)

    result = summary_pipeline.generate_driver_behaviour_summary(
        "scope-a",
        [
            {
                "id": 1,
                "entityName": "David Price",
                "driverId": 312870,
                "startTime": "2026-04-06T12:58:02+00:00",
                "endTime": "2026-04-06T13:10:30+00:00",
                "adasEventsCount": 0,
                "dsmEventsCount": 0,
            }
        ],
    )

    assert result.cached is False
    assert result.event_count == 0
    assert "no tracked ADAS or DSM events" in result.summary


def test_generate_fleet_summary_returns_cached_result(monkeypatch):
    """What: Return cached fleet summary payload when cache already contains an entry.

    Why: Cache hits should bypass AI generation for faster and deterministic responses.

    How: Monkeypatch cache key and cache fetch to return data, fail on AI call, and assert cached response fields.
    """

    monkeypatch.setattr(
        summary_pipeline,
        "build_fleet_summary_cache_key",
        lambda _scope, _data: "fleet_summary:" + "a" * 64,
    )
    monkeypatch.setattr(
        summary_pipeline,
        "get_fleet_summary_cache",
        lambda _cache_key: {
            "summary": "Cached fleet summary",
            "generated_at": "2026-05-08T12:00:00Z",
        },
    )
    monkeypatch.setattr(
        summary_pipeline,
        "generate_fleet_summary_text",
        lambda _data: pytest.fail("AI generation should not run on cache hit"),
    )

    result = summary_pipeline.generate_fleet_summary(
        "scope-a",
        [
            {
                "id": 1,
                "fleetLevelId": 16601,
                "fleetLevelName": "399 Canton",
                "entityName": "Driver A",
                "adasEventsCount": 1,
                "dsmEventsCount": 2,
            }
        ],
    )

    assert result.cache_hit is True
    assert result.summary == "Cached fleet summary"
    assert result.generated_at == "2026-05-08T12:00:00Z"


def test_generate_fleet_summary_generates_and_stores_on_cache_miss(monkeypatch):
    """What: Generate and persist fleet summaries when cache lookup misses.

    Why: Fleet summary endpoint must still return content and backfill cache on first request.

    How: Stub cache miss and AI output, capture cache store payload, and assert response plus persisted values.
    """

    stored = {}

    monkeypatch.setattr(
        summary_pipeline,
        "build_fleet_summary_cache_key",
        lambda _scope, _data: "fleet_summary:" + "b" * 64,
    )
    monkeypatch.setattr(summary_pipeline, "get_fleet_summary_cache", lambda _cache_key: None)
    monkeypatch.setattr(summary_pipeline, "generate_fleet_summary_text", lambda _data: "Generated fleet summary")

    def fake_set_fleet_summary_cache(cache_key, value):
        stored["cache_key"] = cache_key
        stored["value"] = value
        return {
            "cache_key": cache_key,
            "summary": value["summary"],
            "generated_at": "2026-05-08T12:30:00Z",
        }

    monkeypatch.setattr(summary_pipeline, "set_fleet_summary_cache", fake_set_fleet_summary_cache)

    result = summary_pipeline.generate_fleet_summary(
        "scope-a",
        [
            {
                "id": 2,
                "fleetLevelId": 16601,
                "fleetLevelName": "399 Canton",
                "entityName": "Driver B",
                "adasEventsCount": 3,
                "dsmEventsCount": 1,
            }
        ],
    )

    assert result.cache_hit is False
    assert result.summary == "Generated fleet summary"
    assert result.generated_at == "2026-05-08T12:30:00Z"
    assert stored["cache_key"] == "fleet_summary:" + "b" * 64
    assert stored["value"]["summary"] == "Generated fleet summary"


def test_generate_fleet_summary_validates_required_fields():
    """What: Validate required fleet summary request fields.

    Why: Endpoint contract requires a non-empty scope and non-empty data payload.

    How: Invoke generation with missing scope and empty data, then assert HTTP 400 details for each case.
    """

    with pytest.raises(HTTPException) as missing_scope:
        summary_pipeline.generate_fleet_summary("", [{"id": 1}])

    with pytest.raises(HTTPException) as missing_data:
        summary_pipeline.generate_fleet_summary("scope-a", [])

    assert missing_scope.value.status_code == 400
    assert missing_scope.value.detail == "Missing required field: collection_scope"
    assert missing_data.value.status_code == 400
    assert missing_data.value.detail == "Missing required field: data"