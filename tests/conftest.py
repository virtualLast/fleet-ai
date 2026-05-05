import pytest

from models.driver_metrics import DriverMetrics


@pytest.fixture
def sample_driver_metrics() -> DriverMetrics:
    return DriverMetrics(
        id=101,
        name="Alex Driver",
        depot="North Depot",
        forward_collision=0,
        following_distance=0,
        pedestrian_collision=0,
        fatigue=0,
        distraction=0,
        phone_use=0,
        yawning=0,
        smoking=0,
        seatbelt=0,
    )


@pytest.fixture
def sample_event_row() -> dict:
    return {
        "id": 101,
        "entityName": "Alex Driver",
        "fleetLevelName": "North Depot",
        "adasFcwCount": 1,
        "adasHmwCount": 2,
        "adasPcwCount": 0,
        "dsmFatigueCount": 0,
        "dsmDistractionCount": 1,
        "dsmHandheldDevicesCount": 0,
        "dsmYawningCount": 0,
        "dsmSmokingCount": 0,
        "dsmSeatbeltCount": 1,
    }


@pytest.fixture
def sample_collection_data() -> list[dict]:
    return [
        {
            "fleetLevelId": 501,
            "fleetLevelName": "North Depot",
            "entityName": "Alex Driver",
            "adasFcwCount": 1,
            "adasHmwCount": 0,
            "adasPcwCount": 0,
            "adasEventsCount": 1,
            "dsmFatigueCount": 0,
            "dsmNoDriverCount": 0,
            "dsmHandheldDevicesCount": 0,
            "dsmSmokingCount": 0,
            "dsmDistractionCount": 1,
            "dsmYawningCount": 0,
            "dsmSeatbeltCount": 0,
            "dsmEventsCount": 1,
            "vrn": None,
        },
        {
            "fleetLevelId": 502,
            "fleetLevelName": "South Depot",
            "entityName": "Jamie Driver",
            "adasFcwCount": 0,
            "adasHmwCount": 1,
            "adasPcwCount": 0,
            "adasEventsCount": 1,
            "dsmFatigueCount": 1,
            "dsmNoDriverCount": 0,
            "dsmHandheldDevicesCount": 0,
            "dsmSmokingCount": 0,
            "dsmDistractionCount": 0,
            "dsmYawningCount": 0,
            "dsmSeatbeltCount": 0,
            "dsmEventsCount": 1,
            "vrn": None,
        },
    ]