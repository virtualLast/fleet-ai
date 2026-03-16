from models.driver_metrics import DriverMetrics


# -----------------------------
# Function: extract_driver_metrics
# -----------------------------
def extract_driver_metrics(driver) -> DriverMetrics:
    """
    Extracts key safety metrics for a single driver from the raw event data.
    uses .get() to handle missing keys and default to 0 if not present.
    
    Args:
        driver (dict): A dictionary containing raw driver events.
    
    Returns:
        DriverMetrics: A Pydantic model containing only the metrics we care about.
    """
    return DriverMetrics(
        id=driver.get("id", 0),
        name=driver.get("entityName", 'unknown'),
        depot=driver.get("fleetLevelName", 'unknown'),

        forward_collision=driver.get("adasFcwCount", 0),
        following_distance=driver.get("adasHmwCount", 0),
        pedestrian_collision=driver.get("adasPcwCount", 0),

        fatigue=driver.get("dsmFatigueCount", 0),
        distraction=driver.get("dsmDistractionCount", 0),
        phone_use=driver.get("dsmHandheldDevicesCount", 0),
        yawning=driver.get("dsmYawningCount", 0),
        smoking=driver.get("dsmSmokingCount", 0),
        seatbelt=driver.get("dsmSeatbeltCount", 0)
    )