from pydantic import BaseModel


class DriverSummary(BaseModel):

    journey_id: int
    driver: str
    summary: str