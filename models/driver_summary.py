from pydantic import BaseModel


class DriverSummary(BaseModel):

    journey_id: int
    driver: str
    summary: str


class DriverEventRecord(BaseModel):

    fleetLevelId: int
    fleetLevelName: str
    vrn: str | None = None
    adasFcwCount: int = 0
    adasHmwCount: int = 0
    adasPcwCount: int = 0
    adasEventsCount: int = 0
    dsmFatigueCount: int = 0
    dsmNoDriverCount: int = 0
    dsmHandheldDevicesCount: int = 0
    dsmSmokingCount: int = 0
    dsmDistractionCount: int = 0
    dsmYawningCount: int = 0
    dsmSeatbeltCount: int = 0
    dsmEventsCount: int = 0
    entityName: str


class DriverCollectionSummaryRequest(BaseModel):

    collection_scope: str
    data: list[DriverEventRecord]


class DriverCollectionSummary(BaseModel):

    collection_scope: str
    driver_ids: list[int]
    summary: str
    generated_at: str