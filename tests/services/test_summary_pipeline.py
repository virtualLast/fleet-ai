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