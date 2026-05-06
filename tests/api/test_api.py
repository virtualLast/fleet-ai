from fastapi.testclient import TestClient
from fastapi import HTTPException

from api.api import app


def test_post_driver_summary_returns_collection_summary(monkeypatch):
    client = TestClient(app)

    captured = {}

    def fake_generate_event_collection_summary(collection_scope, data):
        captured["collection_scope"] = collection_scope
        captured["data"] = data
        return {
            "collection_scope": collection_scope,
            "driver_ids": [501],
            "summary": "Collection summary",
            "generated_at": "2026-05-05",
        }

    monkeypatch.setattr("api.api.generate_event_collection_summary", fake_generate_event_collection_summary)

    payload = {
        "collection_scope": "scope-a",
        "data": [
            {
                "fleetLevelId": 501,
                "fleetLevelName": "North Depot",
                "vrn": None,
                "adasFcwCount": 0,
                "adasHmwCount": 1,
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
                "entityName": "Alex Driver",
            }
        ],
    }

    response = client.post("/ai/driver-summary", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "collection_scope": "scope-a",
        "driver_ids": [501],
        "summary": "Collection summary",
        "generated_at": "2026-05-05",
    }
    assert captured["collection_scope"] == "scope-a"
    assert captured["data"][0]["fleetLevelId"] == 501


def test_post_driver_summary_validates_payload():
    client = TestClient(app)

    response = client.post("/ai/driver-summary", json={"collection_scope": "scope-a", "data": [{"entityName": "A"}]})

    assert response.status_code == 422


def test_post_driver_summary_by_id_route_returns_single_summary(monkeypatch):
    client = TestClient(app)
    captured = {}

    def fake_generate_single_summary(events_file, journey_id, fallback_payload=None):
        captured["events_file"] = events_file
        captured["journey_id"] = journey_id
        captured["fallback_payload"] = fallback_payload
        return {
            "journey_id": 77,
            "driver": "Jamie Driver",
            "summary": "Journey summary",
        }

    monkeypatch.setattr("api.api.generate_single_summary", fake_generate_single_summary)

    response = client.post("/ai/driver-summary/77")

    assert response.status_code == 200
    assert response.json() == {
        "journey_id": 77,
        "driver": "Jamie Driver",
        "summary": "Journey summary",
    }
    assert captured["events_file"] == "events.json"
    assert captured["journey_id"] == 77
    assert captured["fallback_payload"] is None


def test_post_driver_summary_by_id_route_passes_payload_context(monkeypatch):
    client = TestClient(app)
    captured = {}

    def fake_generate_single_summary(events_file, journey_id, fallback_payload=None):
        captured["events_file"] = events_file
        captured["journey_id"] = journey_id
        captured["fallback_payload"] = fallback_payload
        return {
            "journey_id": journey_id,
            "driver": "Jamie Driver",
            "summary": "Journey summary",
        }

    monkeypatch.setattr("api.api.generate_single_summary", fake_generate_single_summary)

    response = client.post(
        "/ai/driver-summary/77",
        json={
            "collection_scope": "scope-a",
            "data": [
                {
                    "fleetLevelId": 77,
                    "fleetLevelName": "North Depot",
                    "entityName": "Jamie Driver",
                    "adasFcwCount": 1,
                }
            ],
        },
    )

    assert response.status_code == 200
    assert captured["events_file"] == "events.json"
    assert captured["journey_id"] == 77
    assert captured["fallback_payload"]["collection_scope"] == "scope-a"
    assert captured["fallback_payload"]["data"][0]["fleetLevelId"] == 77


def test_post_driver_summary_by_id_returns_400_when_collection_scope_missing(monkeypatch):
    client = TestClient(app)

    def fake_generate_single_summary(_events_file, _journey_id, fallback_payload=None):
        if not (fallback_payload or {}).get("collection_scope"):
            raise HTTPException(status_code=400, detail="Missing required field: collection_scope")

        return {
            "journey_id": 77,
            "driver": "Jamie Driver",
            "summary": "Journey summary",
        }

    monkeypatch.setattr("api.api.generate_single_summary", fake_generate_single_summary)

    response = client.post(
        "/ai/driver-summary/77",
        json={
            "data": [
                {
                    "fleetLevelId": 77,
                    "fleetLevelName": "North Depot",
                    "entityName": "Jamie Driver",
                }
            ]
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing required field: collection_scope"


def test_post_driver_summary_by_id_returns_400_when_data_missing(monkeypatch):
    client = TestClient(app)

    def fake_generate_single_summary(_events_file, _journey_id, fallback_payload=None):
        if not (fallback_payload or {}).get("data"):
            raise HTTPException(status_code=400, detail="Missing required field: data")

        return {
            "journey_id": 77,
            "driver": "Jamie Driver",
            "summary": "Journey summary",
        }

    monkeypatch.setattr("api.api.generate_single_summary", fake_generate_single_summary)

    response = client.post(
        "/ai/driver-summary/77",
        json={"collection_scope": "scope-a"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing required field: data"