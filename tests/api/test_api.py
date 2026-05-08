from fastapi.testclient import TestClient

from api.api import app


def test_post_driver_behaviour_summary_returns_summary(monkeypatch):
    client = TestClient(app)

    captured = {}

    def fake_generate_driver_behaviour_summary(collection_scope, data):
        captured["collection_scope"] = collection_scope
        captured["data"] = data
        return {
            "cached": False,
            "cache_key": "abc123",
            "driver_id": 312870,
            "event_count": 1,
            "summary": "Driver behaviour summary",
        }

    monkeypatch.setattr("api.api.generate_driver_behaviour_summary", fake_generate_driver_behaviour_summary)

    payload = {
        "collection_scope": "scope-a",
        "data": [
            {
                "id": 1392170759,
                "entityName": "David Price",
                "driverId": 312870,
                "vehicleId": 142818,
                "fleetLevelId": 16601,
                "fleetLevelName": "399 Canton",
                "vrn": "BX74OAP",
                "startTime": "2026-04-06T13:13:53+00:00",
                "endTime": "2026-04-06T13:21:09+00:00",
                "adasFcwCount": 0,
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
                "dsmEventsCount": 1,
            }
        ],
    }

    response = client.post("/ai/driver-behaviour-summary", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "cached": False,
        "cache_key": "abc123",
        "driver_id": 312870,
        "event_count": 1,
        "summary": "Driver behaviour summary",
    }
    assert captured["collection_scope"] == "scope-a"
    assert captured["data"][0]["driverId"] == 312870


def test_post_driver_behaviour_summary_returns_422_when_data_missing():
    client = TestClient(app)

    response = client.post("/ai/driver-behaviour-summary", json={"collection_scope": "scope-a"})

    assert response.status_code == 422


def test_post_driver_behaviour_summary_returns_422_when_data_empty():
    client = TestClient(app)
    response = client.post(
        "/ai/driver-behaviour-summary",
        json={"collection_scope": "scope-a", "data": []},
    )

    assert response.status_code == 422


def test_post_driver_behaviour_summary_returns_422_when_required_row_field_missing():
    client = TestClient(app)

    response = client.post(
        "/ai/driver-behaviour-summary",
        json={
            "collection_scope": "scope-a",
            "data": [
                {
                    "id": 1,
                    "entityName": "David Price",
                    "vehicleId": 142818,
                    "fleetLevelId": 16601,
                    "fleetLevelName": "399 Canton",
                    "startTime": "2026-04-06T13:13:53+00:00",
                    "endTime": "2026-04-06T13:21:09+00:00",
                }
            ],
        },
    )

    assert response.status_code == 422


def test_post_driver_behaviour_summary_returns_500_when_pipeline_fails(monkeypatch):
    client = TestClient(app)

    def fake_generate_driver_behaviour_summary(_collection_scope, _data):
        raise RuntimeError("Unexpected failure")

    monkeypatch.setattr("api.api.generate_driver_behaviour_summary", fake_generate_driver_behaviour_summary)

    response = client.post(
        "/ai/driver-behaviour-summary",
        json={
            "collection_scope": "scope-a",
            "data": [
                {
                    "id": 1,
                    "entityName": "David Price",
                    "driverId": 312870,
                    "vehicleId": 142818,
                    "fleetLevelId": 16601,
                    "fleetLevelName": "399 Canton",
                    "startTime": "2026-04-06T13:13:53+00:00",
                    "endTime": "2026-04-06T13:21:09+00:00",
                }
            ],
        },
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


def test_post_fleet_summary_returns_summary(monkeypatch):
    client = TestClient(app)

    captured = {}

    def fake_generate_fleet_summary(collection_scope, data):
        captured["collection_scope"] = collection_scope
        captured["data"] = data
        return {
            "summary": "Fleet-level summary",
            "generated_at": "2026-05-08T12:30:00Z",
            "cache_hit": False,
        }

    monkeypatch.setattr("api.api.generate_fleet_summary", fake_generate_fleet_summary)

    payload = {
        "collection_scope": "scope-fleet-a",
        "data": [
            {
                "id": 1392170759,
                "fleetLevelId": 16601,
                "fleetLevelName": "399 Canton",
                "entityName": "David Price",
                "vrn": "BX74OAP",
                "adasFcwCount": 0,
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
                "dsmEventsCount": 1,
            }
        ],
    }

    response = client.post("/ai/fleet-summary", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "summary": "Fleet-level summary",
        "generated_at": "2026-05-08T12:30:00Z",
        "cache_hit": False,
    }
    assert captured["collection_scope"] == "scope-fleet-a"
    assert captured["data"][0]["fleetLevelId"] == 16601


def test_post_fleet_summary_returns_422_when_data_missing():
    client = TestClient(app)

    response = client.post("/ai/fleet-summary", json={"collection_scope": "scope-a"})

    assert response.status_code == 422


def test_post_fleet_summary_returns_422_when_data_empty():
    client = TestClient(app)
    response = client.post(
        "/ai/fleet-summary",
        json={"collection_scope": "scope-a", "data": []},
    )

    assert response.status_code == 422


def test_post_fleet_summary_returns_500_when_pipeline_fails(monkeypatch):
    client = TestClient(app)

    def fake_generate_fleet_summary(_collection_scope, _data):
        raise RuntimeError("Unexpected failure")

    monkeypatch.setattr("api.api.generate_fleet_summary", fake_generate_fleet_summary)

    response = client.post(
        "/ai/fleet-summary",
        json={
            "collection_scope": "scope-a",
            "data": [
                {
                    "id": 1,
                    "fleetLevelId": 16601,
                    "fleetLevelName": "399 Canton",
                    "entityName": "David Price",
                    "adasEventsCount": 1,
                    "dsmEventsCount": 1,
                }
            ],
        },
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}