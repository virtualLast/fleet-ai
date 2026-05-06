# Fleet AI - Driver Safety Analyst

Fleet AI is a Python project that reads driver safety event data, transforms it into consistent metrics, and generates plain-English safety summaries using OpenAI.

If you are new to Python, this README is designed to explain **what each part does** and **how data moves through the system**.

## What this project does

- Reads driver event records from JSON data.
- Normalizes event counters into typed models.
- Generates:
  - single-journey summaries, and
  - collection-level summaries.
- Caches generated summaries in local JSON files to reduce repeated AI calls.

## How the project works (high-level flow)

### Single journey flow (`POST /ai/driver-summary/{id}` or CLI loop)

1. Load source data from `events.json`.
2. If id exists in file data, convert raw row fields into a `DriverMetrics` model.
3. If id is not in file data, use request payload fallback (`collection_scope` + `data`) and locate matching row by `id` or `fleetLevelId`.
4. Validate required fallback context; return `400` when required fields are missing.
5. Check journey cache first.
6. If no events are present, return a deterministic low-risk sentence.
7. Otherwise call OpenAI to generate a short summary.
8. Store result in cache and return response.

### Collection flow (`POST /ai/driver-summary`)

1. Receive `collection_scope` and `data` payload.
2. Normalize incoming rows (IDs, names, numeric event counters).
3. Check collection cache by `collection_scope`.
4. If all tracked event counters are zero, return deterministic low-risk text.
5. Otherwise call OpenAI for a concise collection insight.
6. Store and return response with `collection_scope`, `driver_ids`, `summary`, `generated_at`.

## Core modules explained

- `main.py`
  - CLI entry point that prints a JSON array of generated driver summaries.
- `api/api.py`
  - FastAPI route layer. Keeps endpoint handlers thin and delegates to services.
- `services/summary_pipeline.py`
  - Main orchestration layer for file/API input, normalization, cache checks, and response model creation.
- `services/summary_service.py`
  - Driver-level summary logic (cache-first, zero-event shortcut, AI path).
- `services/ai_summary.py`
  - Prompt construction and OpenAI request handling.
- `services/driver_metrics.py`
  - Maps raw event JSON fields into normalized `DriverMetrics`.
- `models/`
  - Pydantic schemas used for typed data validation and API response contracts.
- `cache/cache_worker.py`
  - JSON cache load/store helpers for both journey and collection summaries.
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

### `POST /ai/driver-summary`

Generate one summary for a collection payload.

Example request:

```bash
curl -X POST http://localhost:8000/ai/driver-summary \
  -H "Content-Type: application/json" \
  -d '{
    "collection_scope": "fleet=North;period=2026-05-01..2026-05-05",
    "data": [
      {
        "fleetLevelId": 501,
        "fleetLevelName": "North Depot",
        "vrn": null,
        "adasFcwCount": 1,
        "adasHmwCount": 0,
        "adasPcwCount": 0,
        "adasEventsCount": 1,
        "dsmFatigueCount": 0,
        "dsmNoDriverCount": 0,
        "dsmHandheldDevicesCount": 0,
        "dsmSmokingCount": 0,
        "dsmDistractionCount": 1,
        "dsmYawningCount": 0,
        "dsmSeatbeltCount": 0,
        "dsmEventsCount": 1,
        "entityName": "Alex Driver"
      }
    ]
  }'
```

Example response shape:

```json
{
  "collection_scope": "fleet=North;period=2026-05-01..2026-05-05",
  "driver_ids": [501],
  "summary": "...",
  "generated_at": "2026-05-05"
}
```

### `POST /ai/driver-summary/{id}`

Generate one summary for a single journey id.

If the journey id is not present in local `events.json`, include fallback payload context.

Required fields:
- `collection_scope`
- `data[]` with a row matching the requested id by `id` or `fleetLevelId`
- In the matching row: `fleetLevelName`, `entityName`

Optional fields:
- Event counters: `adasFcwCount`, `adasHmwCount`, `adasPcwCount`, `adasEventsCount`, `dsmFatigueCount`, `dsmNoDriverCount`, `dsmHandheldDevicesCount`, `dsmSmokingCount`, `dsmDistractionCount`, `dsmYawningCount`, `dsmSeatbeltCount`, `dsmEventsCount`
- Omitted counters default to `0`.

Example request:

```bash
curl -X POST http://localhost:8000/ai/driver-summary/77 \
  -H "Content-Type: application/json" \
  -d '{
    "collection_scope": "fleet=North;period=2026-05-01..2026-05-05",
    "data": [
      {
        "fleetLevelId": 77,
        "fleetLevelName": "North Depot",
        "entityName": "Alex Driver",
        "adasFcwCount": 1,
        "dsmDistractionCount": 0
      }
    ]
  }'
```

## Caching behavior

- Journey summaries are cached in `cache/summary_cache.json`.
  - Key: `journey_id` converted to string.
- Collection summaries are cached in `cache/event-collection-summary.json`.
  - Key: `collection_scope`.

Caching is used to avoid unnecessary repeated OpenAI calls for the same input scope.

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
   curl -X POST http://localhost:8000/ai/driver-summary/1
   ```

## Troubleshooting

- `Error generating summary` responses:
  - Check `OPENAI_API_KEY` is set.
  - Confirm network access to OpenAI APIs.
- `422 Unprocessable Entity` on `POST /ai/driver-summary`:
  - Verify payload keys and data types match the request model.
- `400` on `POST /ai/driver-summary/{id}`:
  - Include `collection_scope` when the journey id is missing from `events.json`.
  - Include non-empty `data` payload with a row matching the requested id (`id` or `fleetLevelId`).
  - Ensure required matching-row fields are present (`fleetLevelName`, `entityName`).
