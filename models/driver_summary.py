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


class AssessmentConfidenceDerivedFrom(BaseModel):
    """Represent deterministic evidence dimensions used to derive assessment confidence."""

    journey_volume: str | None = None
    event_volume: str | None = None
    event_diversity: str | None = None
    behavioural_distribution: str | None = None
    observation_coverage: str | None = None
    observation_window_days: int | None = None
    observation_duration: str | None = None
    driver_volume: str | None = None


class AssessmentConfidence(BaseModel):
    """Store deterministic assessment confidence and supporting evidence factors."""

    level: str
    derived_from: AssessmentConfidenceDerivedFrom
    reasons: list[str] = Field(default_factory=list)


class DriverRiskDetails(BaseModel):
    """Capture deterministic risk score and discrete risk band for one driver analysis."""

    score: float
    band: str


class DriverAnalysis(BaseModel):
    """Define the canonical structured deterministic single-driver behaviour analysis payload."""

    journey_count: int
    event_count: int
    event_breakdown: dict[str, int]
    risk: DriverRiskDetails
    assessment_confidence: AssessmentConfidence
    dominant_behaviours: list[str]
    primary_risk_dimension: str
    coaching_focus: list[str]


class FleetTopDriver(BaseModel):
    """Represent one top-risk driver in fleet-level structured analysis output."""

    driver_id: int
    name: str
    event_count: int
    primary_behaviour: str


class FleetAnalysis(BaseModel):
    """Define the canonical structured deterministic fleet-level behaviour analysis payload."""

    driver_count: int
    event_count: int
    event_breakdown: dict[str, int]
    top_drivers: list[FleetTopDriver]
    site_clusters: list[str]
    dominant_risk_theme: str
    risk_distribution: str
    anomalies: list[str]
    recommended_actions: list[str]
    assessment_confidence: AssessmentConfidence


class SummaryMetadata(BaseModel):
    """Store cache metadata fields for canonical analysis-summary cache envelopes."""

    cache_key: str
    cache_version: str
    generated_at: str
    model: str


class SummaryTextPayload(BaseModel):
    """Store AI-rendered narrative text as presentation-layer summary payload."""

    text: str


class DriverSummaryCachePayload(BaseModel):
    """Represent canonical cache envelope for single-driver behaviour summaries."""

    metadata: SummaryMetadata
    analysis: DriverAnalysis
    summary: SummaryTextPayload


class FleetSummaryCachePayload(BaseModel):
    """Represent canonical cache envelope for fleet behaviour summaries."""

    metadata: SummaryMetadata
    analysis: FleetAnalysis
    summary: SummaryTextPayload


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