"""Mapping helpers that normalize raw event rows into typed driver metrics."""

from models.driver_metrics import DriverMetrics


# -----------------------------
# Function: extract_driver_metrics
# -----------------------------
def extract_driver_metrics(driver) -> DriverMetrics:
    """
    Extract key safety metrics for a single driver from a raw event record.

    The function uses `dict.get(...)` defaults so missing counters safely fall
    back to `0`, keeping the downstream summary pipeline resilient.
    
    Args:
        driver (dict): A dictionary containing raw driver events.
    
    Returns:
        DriverMetrics: Normalized model used by summary services.
    """
    return DriverMetrics(
        id=driver.get("id", 0),
        name=driver.get("entityName", 'unknown'),
        depot=driver.get("fleetLevelName", 'unknown'),

        # ADAS counters.
        forward_collision=driver.get("adasFcwCount", 0),
        following_distance=driver.get("adasHmwCount", 0),
        pedestrian_collision=driver.get("adasPcwCount", 0),

        # DSM counters.
        fatigue=driver.get("dsmFatigueCount", 0),
        distraction=driver.get("dsmDistractionCount", 0),
        phone_use=driver.get("dsmHandheldDevicesCount", 0),
        yawning=driver.get("dsmYawningCount", 0),
        smoking=driver.get("dsmSmokingCount", 0),
        seatbelt=driver.get("dsmSeatbeltCount", 0)
    )