from pydantic import BaseModel

class DriverMetrics(BaseModel):
    id: int
    name: str
    depot: str

    forward_collision: int
    following_distance: int
    pedestrian_collision: int

    fatigue: int
    distraction: int
    phone_use: int
    yawning: int
    smoking: int
    seatbelt: int