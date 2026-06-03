from pydantic import BaseModel


class DriverMetrics(BaseModel):
    """Normalized per-driver safety metrics consumed by summary services."""

    id: int
    name: str
    depot: str

    # ADAS-related counters (vehicle-assist safety events).
    forward_collision: int
    following_distance: int
    pedestrian_collision: int

    # DSM-related counters (driver state and behavior events).
    fatigue: int
    distraction: int
    phone_use: int
    yawning: int
    smoking: int
    seatbelt: int
