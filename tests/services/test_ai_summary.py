from services.ai_summary import (
    _build_zero_event_collection_summary,
    _is_zero_event_collection,
    generate_collection_summary,
)


def test_is_zero_event_collection_returns_true_for_all_zero_counts():
    collection_data = [
        {
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
            "dsmSeatbeltCount": 0,
            "dsmEventsCount": 0,
        }
    ]

    assert _is_zero_event_collection(collection_data) is True


def test_is_zero_event_collection_returns_false_when_any_count_positive():
    collection_data = [
        {
            "adasFcwCount": 1,
            "adasHmwCount": 0,
            "adasPcwCount": 0,
            "adasEventsCount": 1,
            "dsmFatigueCount": 0,
            "dsmNoDriverCount": 0,
            "dsmHandheldDevicesCount": 0,
            "dsmSmokingCount": 0,
            "dsmDistractionCount": 0,
            "dsmYawningCount": 0,
            "dsmSeatbeltCount": 0,
            "dsmEventsCount": 0,
        }
    ]

    assert _is_zero_event_collection(collection_data) is False


def test_build_zero_event_collection_summary_includes_driver_and_fleet_counts():
    collection_data = [
        {"fleetLevelName": "North Depot"},
        {"fleetLevelName": "South Depot"},
        {"fleetLevelName": "North Depot"},
    ]

    result = _build_zero_event_collection_summary(collection_data)

    assert "3 drivers" in result
    assert "2 fleet groups" in result
    assert "No tracked ADAS or DSM safety events were recorded" in result


def test_generate_collection_summary_returns_empty_data_fallback():
    result = generate_collection_summary([])

    assert result == "No driver event data is available for this collection scope."


def test_generate_collection_summary_returns_error_fallback_when_client_fails(monkeypatch):
    collection_data = [
        {
            "fleetLevelName": "North Depot",
            "adasFcwCount": 3,
            "adasHmwCount": 0,
            "adasPcwCount": 0,
            "adasEventsCount": 3,
            "dsmFatigueCount": 0,
            "dsmNoDriverCount": 0,
            "dsmHandheldDevicesCount": 0,
            "dsmSmokingCount": 0,
            "dsmDistractionCount": 0,
            "dsmYawningCount": 0,
            "dsmSeatbeltCount": 0,
            "dsmEventsCount": 0,
            "entityName": "Alex Driver",
        }
    ]

    class FakeResponses:
        @staticmethod
        def create(**_kwargs):
            raise RuntimeError("OpenAI unavailable")

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr("services.ai_summary.client", FakeClient())

    result = generate_collection_summary(collection_data)

    assert result == "Error generating collection summary."