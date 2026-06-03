# API and Model Contracts

This document describes the active API contracts and the model layer that enforces them.

## 1) Active Endpoints

Defined in `api/api.py`:

- `POST /ai/driver-behaviour-summary`
- `POST /ai/fleet-summary`

Both routes:

- accept Pydantic request models,
- convert `payload.data` rows with `model_dump()`,
- delegate business orchestration to `services.summary_pipeline`,
- convert unexpected failures to `HTTPException(status_code=500)`.

## 2) Driver Behaviour Endpoint Contract

### Route signature

```python
@app.post("/ai/driver-behaviour-summary", response_model=DriverBehaviourSummary)
def summarize_driver_behaviour(payload: DriverBehaviourSummaryRequest):
    collection_data = [event.model_dump() for event in payload.data]
    return generate_driver_behaviour_summary(payload.collection_scope, collection_data)
```

### Request model

`models/driver_summary.py::DriverBehaviourSummaryRequest`

- `collection_scope: str`
- `data: list[DriverBehaviourEventRecord] = Field(min_length=1)`

`DriverBehaviourEventRecord` includes:

- identity/context fields (`id`, `entityName`, `driverId`, `vehicleId`, `fleetLevelId`, `fleetLevelName`, `vrn`),
- optional position tuples (`startPosn`, `endPosn`),
- timestamps (`startTime`, `endTime`),
- ADAS/DSM counters.

### Response model

`models/driver_summary.py::DriverBehaviourSummary`

- `cached: bool`
- `cache_key: str`
- `driver_id: int`
- `event_count: int`
- `summary: str`

### Example request

```json
{
  "collection_scope": "scope-driver-1",
  "data": [
    {
      "id": 1392170759,
      "entityName": "David Price",
      "driverId": 312870,
      "vehicleId": 16608,
      "fleetLevelId": 16601,
      "fleetLevelName": "399 Canton",
      "vrn": "BX74OAP",
      "startTime": "2026-04-06T13:13:53+00:00",
      "endTime": "2026-04-06T13:21:09+00:00",
      "adasEventsCount": 0,
      "dsmEventsCount": 1,
      "dsmSeatbeltCount": 1
    }
  ]
}
```

### Example response

```json
{
  "cached": false,
  "cache_key": "73f36a56689d86af148e911cb94380d400c8dd3035a709dfd7fb84e9b91cfb75",
  "driver_id": 312870,
  "event_count": 1,
  "summary": "Driver behaviour summary text..."
}
```

## 3) Fleet Endpoint Contract

### Route signature

```python
@app.post("/ai/fleet-summary", response_model=FleetSummary)
def summarize_fleet(payload: FleetSummaryRequest):
    collection_data = [event.model_dump() for event in payload.data]
    return generate_fleet_summary(payload.collection_scope, collection_data)
```

### Request model

`models/driver_summary.py::FleetSummaryRequest`

- `collection_scope: str`
- `data: list[FleetSummaryEventRecord] = Field(min_length=1)`

`FleetSummaryEventRecord` extends `BaseEventRecord` and requires:

- `id: int`
- all common fleet + ADAS/DSM fields inherited from `BaseEventRecord`.

### Response model

`models/driver_summary.py::FleetSummary`

- `summary: str`
- `generated_at: str`
- `cache_hit: bool`

### Example request

```json
{
  "collection_scope": "scope-fleet-a",
  "data": [
    {
      "id": 1392170759,
      "fleetLevelId": 16601,
      "fleetLevelName": "399 Canton",
      "entityName": "David Price",
      "vrn": "BX74OAP",
      "adasEventsCount": 1,
      "dsmEventsCount": 1
    }
  ]
}
```

### Example response

```json
{
  "summary": "Fleet-level operational summary text...",
  "generated_at": "2026-05-08T12:30:00Z",
  "cache_hit": false
}
```

## 4) Error Contract Notes

- FastAPI/Pydantic validation failures return `422` before route business logic runs.
- Route handlers convert semantic `ValueError` to `400`.
- Unexpected runtime failures are logged and returned as `500`.

This behavior is covered by `tests/api/test_api.py`.

## 5) Extended Internal Contracts

The model module also defines internal structured payload models used to describe cache and analysis shapes:

- `AssessmentConfidenceDerivedFrom`
- `AssessmentConfidence`
- `DriverRiskDetails`
- `DriverAnalysis`
- `FleetTopDriver`
- `FleetAnalysis`
- `SummaryMetadata`
- `SummaryTextPayload`
- `DriverSummaryCachePayload`
- `FleetSummaryCachePayload`

These models are useful references when tracing cache payload and pipeline analysis fields.