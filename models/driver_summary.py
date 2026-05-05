from pydantic import BaseModel


class DriverSummary(BaseModel):
    """Response model for one summarized journey."""

    journey_id: int
    driver: str
    summary: str


class DriverEventRecord(BaseModel):
    """Input row model for collection summarization requests."""

    fleetLevelId: int
    fleetLevelName: str
    vrn: str | None = None

    # ADAS counters.
    adasFcwCount: int = 0
    adasHmwCount: int = 0
    adasPcwCount: int = 0
    adasEventsCount: int = 0

    # DSM counters.
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
    """Request payload for `POST /ai/driver-summary`."""

    # Unique key that defines the dataset scope (used as collection cache key).
    collection_scope: str
    data: list[DriverEventRecord]


class DriverCollectionSummary(BaseModel):
    """Response model for one generated collection summary."""

    collection_scope: str
    # List of normalized identifiers included in the summarized collection.
    driver_ids: list[int]
    summary: str
    # Date stamp showing when the summary entry was generated and cached.
    generated_at: str