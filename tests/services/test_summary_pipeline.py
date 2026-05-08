import pytest
from fastapi import HTTPException

from services import summary_pipeline


def test_normalize_collection_data_handles_id_fallback_uniqueness_and_coercion():
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
    with pytest.raises(HTTPException) as missing_data_exc:
        summary_pipeline._validate_driver_behaviour_payload("scope-a", None)

    assert missing_data_exc.value.status_code == 400
    assert missing_data_exc.value.detail == "Missing required field: data"

    with pytest.raises(HTTPException) as empty_data_exc:
        summary_pipeline._validate_driver_behaviour_payload("scope-a", [])

    assert empty_data_exc.value.status_code == 400
    assert empty_data_exc.value.detail == "Missing required field: data"


def test_validate_driver_behaviour_payload_rejects_invalid_driver_id():
    with pytest.raises(HTTPException) as exc_info:
        summary_pipeline._validate_driver_behaviour_payload(
            "scope-a",
            [{"driverId": "bad", "startTime": "2026-04-06T12:58:02+00:00", "endTime": "2026-04-06T13:10:30+00:00"}],
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid driverId at row 0"


def test_validate_driver_behaviour_payload_rejects_malformed_timestamps():
    with pytest.raises(HTTPException) as exc_info:
        summary_pipeline._validate_driver_behaviour_payload(
            "scope-a",
            [{"driverId": 312870, "startTime": "not-a-timestamp", "endTime": "2026-04-06T13:10:30+00:00"}],
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Malformed timestamp: startTime"


def test_validate_driver_behaviour_payload_rejects_mixed_driver_ids():
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


def test_generate_event_collection_summary_returns_cached_result(monkeypatch):
    cache = {
        "scope-1": {
            "collection_scope": "scope-1",
            "driver_ids": [7, 8],
            "summary": "Cached collection summary",
            "generated_at": "2026-05-05",
        }
    }

    monkeypatch.setattr(summary_pipeline, "load_event_collection_cache", lambda: cache)
    monkeypatch.setattr(
        summary_pipeline,
        "get_cached_event_collection_summary",
        lambda loaded_cache, collection_scope: loaded_cache.get(collection_scope),
    )
    monkeypatch.setattr(
        summary_pipeline,
        "generate_collection_summary",
        lambda _data: pytest.fail("AI generation should not run on cache hit"),
    )

    result = summary_pipeline.generate_event_collection_summary("scope-1", [{"fleetLevelId": 7}])

    assert result.collection_scope == "scope-1"
    assert result.driver_ids == [7, 8]
    assert result.summary == "Cached collection summary"


def test_generate_event_collection_summary_generates_and_saves_on_cache_miss(monkeypatch):
    cache = {}
    save_called = {"count": 0}

    monkeypatch.setattr(summary_pipeline, "load_event_collection_cache", lambda: cache)
    monkeypatch.setattr(summary_pipeline, "get_cached_event_collection_summary", lambda _cache, _scope: None)
    monkeypatch.setattr(summary_pipeline, "generate_collection_summary", lambda _data: "Generated collection summary")

    def fake_store_event_collection_summary(target_cache, collection_scope, driver_ids, summary):
        target_cache[collection_scope] = {
            "collection_scope": collection_scope,
            "driver_ids": driver_ids,
            "summary": summary,
            "generated_at": "2026-05-05",
        }

    def fake_save_event_collection_cache(_cache):
        save_called["count"] += 1

    monkeypatch.setattr(summary_pipeline, "store_event_collection_summary", fake_store_event_collection_summary)
    monkeypatch.setattr(summary_pipeline, "save_event_collection_cache", fake_save_event_collection_cache)

    result = summary_pipeline.generate_event_collection_summary(
        "scope-2",
        [
            {
                "fleetLevelId": 11,
                "fleetLevelName": "North",
                "entityName": "Driver A",
                "adasFcwCount": 1,
            },
            {
                "fleetLevelId": 12,
                "fleetLevelName": "South",
                "entityName": "Driver B",
                "adasFcwCount": 0,
            },
        ],
    )

    assert result.collection_scope == "scope-2"
    assert result.driver_ids == [11, 12]
    assert result.summary == "Generated collection summary"
    assert save_called["count"] == 1


def test_generate_single_summary_returns_driver_summary(monkeypatch):
    monkeypatch.setattr(
        summary_pipeline,
        "load_cache",
        lambda: {"200": {"driver": "Alex Driver", "summary": "Driver summary text"}},
    )
    monkeypatch.setattr(
        summary_pipeline,
        "save_cache",
        lambda _cache: pytest.fail("Cache should not be saved on cache hit"),
    )

    result = summary_pipeline.generate_single_summary(200)

    assert result.journey_id == 200
    assert result.driver == "Alex Driver"
    assert result.summary == "Driver summary text"


def test_generate_single_summary_returns_404_when_cache_misses_without_payload(monkeypatch):
    monkeypatch.setattr(summary_pipeline, "load_cache", lambda: {})

    with pytest.raises(HTTPException) as exc_info:
        summary_pipeline.generate_single_summary(404)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Journey summary not found"


def test_generate_single_summary_uses_fallback_payload_when_journey_missing(monkeypatch):
    save_called = {"count": 0}

    monkeypatch.setattr(summary_pipeline, "load_cache", lambda: {})
    monkeypatch.setattr(
        summary_pipeline,
        "generate_driver_journey_collection_summary",
        lambda _data: "Fallback collection summary",
    )
    monkeypatch.setattr(summary_pipeline, "save_cache", lambda _cache: save_called.__setitem__("count", 1))

    result = summary_pipeline.generate_single_summary(
        404,
        {
            "collection_scope": "scope-a",
            "data": [
                {
                    "fleetLevelId": 404,
                    "fleetLevelName": "North Depot",
                    "entityName": "Fallback Driver",
                    "adasFcwCount": 1,
                }
            ],
        },
    )

    assert result.journey_id == 404
    assert result.driver == "Fallback Driver"
    assert result.summary == "Fallback collection summary"
    assert save_called["count"] == 1


def test_generate_single_summary_returns_400_when_collection_scope_missing(monkeypatch):
    monkeypatch.setattr(summary_pipeline, "load_cache", lambda: {})

    with pytest.raises(HTTPException) as exc_info:
        summary_pipeline.generate_single_summary(
            404,
            {
                "data": [
                    {
                        "fleetLevelId": 404,
                        "fleetLevelName": "North Depot",
                        "entityName": "Fallback Driver",
                    }
                ]
            },
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Missing required field: collection_scope"


def test_generate_single_summary_returns_400_when_data_missing(monkeypatch):
    monkeypatch.setattr(summary_pipeline, "load_cache", lambda: {})

    with pytest.raises(HTTPException) as exc_info:
        summary_pipeline.generate_single_summary(
            404,
            {"collection_scope": "scope-a"},
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Missing required field: data"


def test_generate_single_summary_uses_cached_summary_for_payload_collection(monkeypatch):
    monkeypatch.setattr(
        summary_pipeline,
        "load_cache",
        lambda: {"404": {"summary": "Cached payload summary"}},
    )
    monkeypatch.setattr(
        summary_pipeline,
        "generate_driver_journey_collection_summary",
        lambda _data: pytest.fail("AI generation should not run on cache hit"),
    )
    monkeypatch.setattr(
        summary_pipeline,
        "save_cache",
        lambda _cache: pytest.fail("Cache should not be saved on cache hit"),
    )

    result = summary_pipeline.generate_single_summary(
        404,
        {
            "collection_scope": "scope-a",
            "data": [
                {
                    "fleetLevelId": 404,
                    "fleetLevelName": "North Depot",
                    "entityName": "Fallback Driver",
                    "adasFcwCount": 1,
                }
            ],
        },
    )

    assert result.journey_id == 404
    assert result.driver == "Fallback Driver"
    assert result.summary == "Cached payload summary"