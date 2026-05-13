from pydantic import BaseModel, Field


class DriverSummary(BaseModel):
    """Response model for one summarized journey."""

    journey_id: int
    driver: str
    summary: str


class BaseEventRecord(BaseModel):
    """Base model for fleet-linked rows with ADAS/DSM counters."""

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


class DriverCollectionSummary(BaseModel):
    """Response model for one generated collection summary."""

    collection_scope: str
    # List of normalized identifiers included in the summarized collection.
    driver_ids: list[int]
    summary: str
    # Date stamp showing when the summary entry was generated and cached.
    generated_at: str


class DriverBehaviourEventRecord(BaseModel):
    """Input row model for collection-based driver behaviour summary requests."""

    id: int
    entityName: str
    driverId: int
    vehicleId: int
    fleetLevelId: int
    fleetLevelName: str
    vrn: str | None = None
    # Position arrays are expected as [lat, lng, address].
    startPosn: tuple[str, str, str] | None = None
    endPosn: tuple[str, str, str] | None = None
    startTime: str
    endTime: str

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


class DriverBehaviourSummaryRequest(BaseModel):
    """Request payload for `POST /ai/driver-behaviour-summary`."""

    collection_scope: str
    data: list[DriverBehaviourEventRecord] = Field(min_length=1)


class DriverBehaviourSummary(BaseModel):
    """Response model for collection-based driver behaviour summary endpoint."""

    cached: bool
    cache_key: str
    driver_id: int
    event_count: int
    summary: str


class FleetSummaryEventRecord(BaseEventRecord):
    """Input row model for fleet-level AI summary requests."""

    id: int


class FleetSummaryRequest(BaseModel):
    """Request payload for `POST /ai/fleet-summary`."""

    collection_scope: str
    data: list[FleetSummaryEventRecord] = Field(min_length=1)


class FleetSummary(BaseModel):
    """Response model for fleet-level AI summary endpoint."""

    summary: str
    generated_at: str
    cache_hit: bool