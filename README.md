# Fleet AI - Driver Safety Analyst

Fleet AI is a Python project that reads driver safety event data, transforms it into consistent metrics, and generates plain-English safety summaries using OpenAI.

If you are new to Python, this README is designed to explain **what each part does** and **how data moves through the system**.

## What this project does

- Reads driver event records from JSON data.
- Normalizes event counters into typed models.
- Generates collection-based driver behaviour summaries.
- Caches generated summaries in local JSON files to reduce repeated AI calls.

## How the project works (high-level flow)

### Driver behaviour flow (`POST /ai/driver-behaviour-summary`)

1. Receive `collection_scope` and `data` payload for one driver.
2. Validate semantic contract (non-empty `data`, coherent `driverId`, parseable timestamps).
3. Normalize rows for deterministic caching (sort, coerce numeric strings to ints, exclude irrelevant fields).
4. Build deterministic cache key from:
   - `CACHE_SCHEMA_VERSION`
   - `collection_scope`
   - normalized `data`
5. Check filesystem cache at `cache/driver_behaviour/{sha256}.json`.
6. On cache miss:
   - run deterministic risk engine (`services/risk/driver_risk_engine.py`) to compute:
     - behaviour breakdown
     - risk score + risk level
     - confidence
     - primary concerns
     - risk model version
   - build strict AI payload using only deterministic outputs (`risk_profile` + `behaviour_summary`)
   - if all tracked behaviour counters are zero, return deterministic static summary (no AI request)
   - otherwise generate AI narrative summary
   - persist cache entry metadata + summary
7. Return `{cached, cache_key, driver_id, event_count, summary}`.

### Fleet summary flow (`POST /ai/fleet-summary`)

1. Receive `collection_scope` and aggregated fleet-level `data` payload.
2. Validate semantic contract (`collection_scope` present, non-empty `data`).
3. Normalize dataset with shared normalization utilities for deterministic cache semantics.
4. Build deterministic fleet cache key from:
   - `CACHE_SCHEMA_VERSION`
   - `collection_scope`
   - normalized `data`
5. Check cache via `cache/cache_worker.py` using `fleet_summary:{sha256}` key.
6. On cache miss:
   - send full normalized dataset to fleet AI narrative function
   - generate concise fleet-level operational summary
   - store cache entry with cache-layer metadata (`generated_at`)
7. Return `{summary, generated_at, cache_hit}`.

Ownership rule:
- The risk engine is the only component allowed to interpret behavioural data.
- Pipeline, API, and AI layers must treat risk-engine output as immutable truth.

## Core modules explained

- `main.py`
  - CLI entry point that prints a JSON array of generated driver summaries.
- `api/api.py`
  - FastAPI route layer. Keeps endpoint handlers thin and delegates to services.
- `services/summary_pipeline.py`
  - Main orchestration layer for payload validation, deterministic normalization/hash, cache checks, risk-engine invocation, and response model creation.
- `services/risk/driver_risk_engine.py`
  - Deterministic risk-analysis source of truth (weights, scoring, confidence, primary concerns, model versioning).
- `services/ai_summary.py`
  - Narrative-only prompt construction and OpenAI request handling; does not compute/override risk.
- `services/driver_metrics.py`
  - Maps raw event JSON fields into normalized `DriverMetrics`.
- `models/`
  - Pydantic schemas used for typed data validation and API response contracts.
- `cache/cache_worker.py`
  - Cache load/store helpers including deterministic hash-based filesystem cache entries.
- `util/data_loader.py`
  - Minimal file loader utility for JSON event input.
- `tests/`
  - Unit/API tests for service behavior, pipeline logic, and endpoints.

## Setup and installation

### Prerequisites

- Python 3.12+ recommended
- OpenAI API key

### 1) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 3) Configure environment variables

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY='your-api-key-here'
```

Or export the variable in your shell:

```bash
export OPENAI_API_KEY='your-api-key-here'
```

> Never commit real API keys to source control.

## Running the project

### Run the CLI flow

```bash
python3 main.py
```

This prints a JSON list where each item includes:
- `journey_id`
- `driver`
- `summary`

### Run the API locally with Uvicorn

```bash
uvicorn api.api:app --host 0.0.0.0 --port 8000 --reload
```

## API endpoints

### `POST /ai/driver-behaviour-summary`

Generate one behaviour summary for a single-driver collection payload.

Example request:

```bash
curl -X POST http://localhost:8000/ai/driver-behaviour-summary \
  -H "Content-Type: application/json" \
  -d '{
    "collection_scope": "/frink/vision/journey?...",
    "data": [
      {
        "id": 1392170759,
        "entityName": "David Price",
        "driverId": 312870,
        "vehicleId": 142818,
        "fleetLevelId": 16601,
        "fleetLevelName": "399 Canton",
        "vrn": "BX74OAP",
        "startTime": "2026-04-06T13:13:53+00:00",
        "endTime": "2026-04-06T13:21:09+00:00",
        "adasFcwCount": 0,
        "adasHmwCount": 0,
        "adasPcwCount": 0,
        "adasEventsCount": 0,
        "dsmFatigueCount": 0,
        "dsmNoDriverCount": 0,
        "dsmHandheldDevicesCount": 0,
        "dsmSmokingCount": 0,
        "dsmDistractionCount": 0,
        "dsmYawningCount": 0,
        "dsmSeatbeltCount": 1,
        "dsmEventsCount": 1,
        "startPosn": ["51.47658", "-3.18497", "Plantagenet Street, Cardiff, UK"],
        "endPosn": ["51.48223", "-3.20308", "5 Library Street, Cardiff, UK"]
      }
    ]
  }'
```

### `POST /ai/fleet-summary`

Generate one aggregate fleet-level summary for a collection payload.

Example request:

```bash
curl -X POST http://localhost:8000/ai/fleet-summary \
  -H "Content-Type: application/json" \
  -d '{
    "collection_scope": "scope-fleet-a",
    "data": [
      {
        "id": 1392170759,
        "fleetLevelId": 16601,
        "fleetLevelName": "399 Canton",
        "vrn": "BX74OAP",
        "adasFcwCount": 0,
        "adasHmwCount": 0,
        "adasPcwCount": 0,
        "adasEventsCount": 1,
        "dsmFatigueCount": 0,
        "dsmNoDriverCount": 0,
        "dsmHandheldDevicesCount": 0,
        "dsmSmokingCount": 0,
        "dsmDistractionCount": 0,
        "dsmYawningCount": 0,
        "dsmSeatbeltCount": 0,
        "dsmEventsCount": 1,
        "entityName": "David Price"
      }
    ]
  }'
```

Example response shape:

```json
{
  "summary": "...",
  "generated_at": "2026-05-08T12:30:00Z",
  "cache_hit": false
}
```

Example response shape:

```json
{
  "cached": false,
  "cache_key": "<sha256>",
  "driver_id": 312870,
  "event_count": 1,
  "summary": "..."
}
```

### Internal deterministic AI input contract (pipeline -> AI service)

The AI layer receives only deterministic backend output:

```json
{
  "driver_id": 402495,
  "driver_name": "Martin Hever",
  "journey_count": 14,
  "risk_profile": {
    "model_version": "v1",
    "risk_level": "low|medium|high",
    "risk_score": 0.0,
    "confidence": "low|medium|high",
    "primary_concerns": ["seatbelt"],
    "requires_intervention": false
  },
  "behaviour_summary": {
    "seatbelt_events": 14,
    "fatigue_events": 0,
    "distraction_events": 0,
    "adas_events": 0
  }
}
```

Notes:
- `behaviour_summary` is a pipeline-level projection of risk-engine breakdown output.
- Source values come from `DriverRiskEngine.compute_behaviour_breakdown(...)` and use each behaviour's `raw_event_count` (not `journey_presence_count`) to populate the flat `*_events` fields shown above.

AI non-goals:
- Must not infer severity from raw event counts.
- Must not compute or override risk scoring.
- Must not introduce behavioural categories not present in input.
- Must not perform risk modelling, behavioural classification, thresholding, or weight logic.

## Caching behavior

- Behaviour summaries are cached as one file per deterministic key:
  - Directory: `cache/driver_behaviour/`
  - Filename: `{sha256}.json`
- Hash input source:
  - `version` (`CACHE_SCHEMA_VERSION`, currently `v1`)
  - `collection_scope`
  - normalized `data`
- This prevents cache fragmentation due to row ordering, numeric string/int differences, and irrelevant metadata changes.
- Cache keys are deterministic backend artifacts and must never include AI-generated text.
- Bumping `CACHE_SCHEMA_VERSION` invalidates old cache entries when normalization/prompt/schema contracts change.

Fleet summary cache behavior:
- Fleet summary entries are stored by cache key in the existing cache worker backend (`cache/event-collection-summary.json`).
- Key format: `fleet_summary:{sha256}` where SHA256 is built from `CACHE_SCHEMA_VERSION + collection_scope + normalized data`.
- Cache metadata (`generated_at`) is created by cache worker on write.
- Fleet cache reads apply TTL filtering in cache worker (default 1 hour; configurable via `FLEET_SUMMARY_CACHE_TTL_SECONDS`).

## Running tests

Run all tests:

```bash
.venv/bin/python -m pytest -q
```

Run a specific suite:

```bash
.venv/bin/python -m pytest tests/services/test_summary_pipeline.py -q
```

## Run the API with Docker

1. Ensure Docker external networks exist (only needed once per machine):

   ```bash
   docker network create lightfoot || true
   docker network create caddy_web || true
   ```

2. Ensure `OPENAI_API_KEY` is available (`.env` or shell export).

3. Start containers:

   ```bash
   docker compose up --build -d
   ```

4. Validate local endpoint:

   ```bash
   curl -X POST http://localhost:8000/ai/driver-behaviour-summary \
     -H "Content-Type: application/json" \
     -d '{"collection_scope":"scope-a","data":[{"id":1,"entityName":"Driver","driverId":1,"vehicleId":1,"fleetLevelId":1,"fleetLevelName":"North","startTime":"2026-04-06T13:13:53+00:00","endTime":"2026-04-06T13:21:09+00:00"}]}'
   ```

## Troubleshooting

- `Error generating summary` responses:
  - Check `OPENAI_API_KEY` is set.
  - Confirm network access to OpenAI APIs.
- `422 Unprocessable Entity` on `POST /ai/driver-behaviour-summary`:
  - Verify payload keys and required row fields (`id`, `entityName`, `driverId`, `vehicleId`, `fleetLevelId`, `fleetLevelName`, `startTime`, `endTime`).
- `400` from behaviour pipeline validation:
  - Ensure `collection_scope` is present and non-empty.
  - Ensure `data` is non-empty and all rows belong to the same positive `driverId`.
  - Ensure `startTime`/`endTime` values are valid timestamps.
