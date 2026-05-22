# Fleet AI Project Architecture Guide

## Who This Guide Is For

This guide is for a new Python developer who wants to understand how this project is put together, what each part does, and why the design is split across several files instead of being written as one large script.

The project is called Fleet AI. It receives fleet and driver safety event data, turns that data into consistent Python structures, calculates deterministic risk where needed, asks OpenAI to write plain-English summaries, caches results, and returns API responses.

The most important idea in this codebase is separation of responsibilities:

- `api/api.py` receives HTTP requests.
- `models/driver_summary.py` defines the shapes of requests and responses.
- `services/summary_pipeline.py` coordinates the main business flow.
- `services/risk/driver_risk_engine.py` calculates driver risk in normal Python code.
- `services/ai_summary.py` asks OpenAI to turn already-prepared data into prose.
- `cache/cache_worker.py` reads and writes cached summaries.

That split is deliberate. It keeps web routing, validation, risk calculation, AI prompting, and file caching from becoming tangled together.

## What The Project Does

Fleet AI currently exposes two active API endpoints in `api/api.py`:

```python
@app.post("/ai/driver-behaviour-summary", response_model=DriverBehaviourSummary)
def summarize_driver_behaviour(payload: DriverBehaviourSummaryRequest):
    collection_data = [event.model_dump() for event in payload.data]
    return generate_driver_behaviour_summary(payload.collection_scope, collection_data)
```

The real function includes error handling, but the simplified version above shows the core flow from `api/api.py::summarize_driver_behaviour()`: receive a validated request, convert Pydantic models into dictionaries, and delegate the work to `services.summary_pipeline.generate_driver_behaviour_summary()`.

The second active endpoint is fleet-level:

```python
@app.post("/ai/fleet-summary", response_model=FleetSummary)
def summarize_fleet(payload: FleetSummaryRequest):
    collection_data = [event.model_dump() for event in payload.data]
    return generate_fleet_summary(payload.collection_scope, collection_data)
```

This mirrors `api/api.py::summarize_fleet()`. The endpoint receives a fleet dataset and delegates to `services.summary_pipeline.generate_fleet_summary()`.

In plain English, the project answers two questions:

- For one driver over a set of journeys, what behaviour risks are visible?
- For a whole fleet dataset, what operational safety patterns stand out?

The project uses deterministic Python logic for risk scoring and OpenAI for narrative writing. That distinction matters: safety risk should be repeatable and testable, while the AI is used to make the result easier for a human to read.

## Big Picture Architecture

The codebase is small, but it already follows a layered service design:

```text
HTTP request
  -> api/api.py
  -> models/driver_summary.py
  -> services/summary_pipeline.py
  -> services/risk/driver_risk_engine.py
  -> services/ai_summary.py
  -> cache/cache_worker.py
  -> HTTP response
```

The exact path depends on which endpoint is called, but this diagram shows the main idea: each layer owns a different kind of work.

## Layer By Layer

### API Layer

The API layer lives in `api/api.py`.

It owns HTTP-specific behavior:

- Creating the FastAPI app with `app = FastAPI()`.
- Registering endpoints with decorators such as `@app.post(...)`.
- Accepting Pydantic request models as function parameters.
- Converting model objects into dictionaries with `model_dump()`.
- Translating unexpected failures into HTTP 500 responses.

The API layer does not calculate risk or build prompts. That work belongs deeper in the service layer.

### Model Layer

The model layer lives mainly in `models/driver_summary.py`.

It defines Pydantic classes such as:

- `DriverBehaviourSummaryRequest`
- `DriverBehaviourEventRecord`
- `DriverBehaviourSummary`
- `FleetSummaryRequest`
- `FleetSummaryEventRecord`
- `FleetSummary`

Pydantic models give the API a contract. For example, `DriverBehaviourEventRecord` says a driver behaviour row must include fields such as `id`, `entityName`, `driverId`, `vehicleId`, `fleetLevelId`, `fleetLevelName`, `startTime`, and `endTime`.

That means FastAPI can reject badly shaped requests before the pipeline code runs.

### Pipeline Layer

The pipeline layer lives in `services/summary_pipeline.py`.

This file is the main coordinator. It does not just call AI directly. It performs the sequence of work needed to turn a request into a reliable response:

- Validate business rules with `_validate_driver_behaviour_payload()`.
- Normalize rows with `_normalize_driver_behaviour_hash_data()`.
- Build cache keys with `_build_driver_behaviour_cache_key()`.
- Check cache with `load_driver_behaviour_cache_entry()`.
- Build deterministic risk data with `_aggregate_driver_behaviour_payload()`.
- Call the AI narrative layer only when needed.
- Store cache entries with `store_driver_behaviour_cache_entry()`.

For fleet summaries, `generate_fleet_summary()` follows the same general shape: validate, normalize, check cache, generate text on a miss, store, return.

### Risk Engine Layer

The risk engine lives in `services/risk/driver_risk_engine.py`.

The central class is `DriverRiskEngine`. It owns deterministic risk analysis:

- `compute_behaviour_breakdown()` counts raw events and journey presence.
- `calculate_weighted_risk_score()` calculates a score from weighted journey presence.
- `classify_risk_level()` maps the score to `low`, `medium`, or `high`.
- `compute_confidence()` estimates confidence from signal diversity.
- `derive_primary_concerns()` ranks the top concern labels.
- `build_risk_profile()` combines those pieces into one risk profile dictionary.

This layer is intentionally separate from OpenAI. The project wants risk scoring to be testable and repeatable.

### AI Narrative Layer

The AI layer lives in `services/ai_summary.py`.

Its job is to write summaries, not to decide risk. Important functions include:

- `generate_driver_behaviour_aggregated_summary()`
- `generate_fleet_summary_text()`
- `generate_collection_summary()`
- `generate_driver_journey_collection_summary()`

Before data is sent to OpenAI, helper functions such as `_sanitize_aggregated_behaviour_payload()` and `_sanitize_fleet_summary_prompt_data()` whitelist fields and coerce values into predictable types.

### Cache Layer

The cache layer lives in `cache/cache_worker.py`.

It owns local JSON caching:

- `build_driver_behaviour_cache_key()` creates SHA256 keys from normalized data.
- `load_driver_behaviour_cache_entry()` reads driver behaviour cache files.
- `store_driver_behaviour_cache_entry()` writes driver behaviour cache files.
- `build_fleet_summary_cache_key()` creates prefixed fleet summary keys.
- `get_fleet_summary_cache()` reads fleet cache entries and applies TTL expiry.
- `set_fleet_summary_cache()` writes fleet cache entries with metadata.

Caching matters because AI calls can be slow, expensive, and non-deterministic. If the same normalized input appears again, the project can return the previous summary.

### Utility Layer

Shared helpers live in `util/`.

The most important file is `util/summary_normalization.py`. Its `normalize_summary_dataset()` function takes raw dictionaries and produces stable normalized dictionaries by coercing integer fields, coercing text fields, and sorting rows.

### Test Layer

Tests live in `tests/`.

The tests mirror the layers:

- `tests/api/test_api.py` checks endpoint behavior.
- `tests/services/test_summary_pipeline.py` checks orchestration and validation.
- `tests/services/test_driver_risk_engine.py` checks deterministic risk scoring.
- `tests/services/test_ai_summary.py` checks AI prompt sanitization and fallbacks.
- `tests/cache/test_cache_worker.py` checks cache validation and expiry.

This is a useful habit in Python projects: tests should prove the important behavior of each layer, not just check that functions can be called.

## Python Concepts Used In This Project

### Modules And Imports

A Python file is often called a module. For example, `api/api.py` is a module, and `services/summary_pipeline.py` is another module.

Files use `import` statements to reuse code from other modules:

```python
from services.summary_pipeline import generate_driver_behaviour_summary, generate_fleet_summary
from models.driver_summary import DriverBehaviourSummaryRequest, FleetSummaryRequest
```

This means `api/api.py` can call functions from `services/summary_pipeline.py` and use classes from `models/driver_summary.py`.

### Functions

A function is a named block of reusable behavior.

This project uses functions for small operations and for major workflows:

```python
def generate_fleet_summary(collection_scope: str, data: list[dict]) -> FleetSummary:
    """Generate aggregate fleet-level summary using cache-first orchestration."""
```

The `def` keyword defines the function. The type hints say `collection_scope` should be a string, `data` should be a list of dictionaries, and the function returns a `FleetSummary`.

### Classes

A class groups related data and behavior.

`DriverRiskEngine` is a class because the risk engine has several related methods and shared constants:

```python
class DriverRiskEngine:
    RISK_MODEL_VERSION = "v1"

    BEHAVIOUR_WEIGHTS = {
        "dsm_fatigue": 5,
        "dsm_distraction": 4,
        "adas_events": 3,
    }
```

The real class contains more weights and methods. Keeping them together makes it clear that these constants belong to the risk model.

### Pydantic Models

Pydantic models are classes that describe data shapes. FastAPI uses them to validate request bodies and responses.

Example from `models/driver_summary.py`:

```python
class FleetSummary(BaseModel):
    """Response model for fleet-level AI summary endpoint."""

    summary: str
    generated_at: str
    cache_hit: bool
```

This says a fleet summary response must contain:

- `summary`, a string.
- `generated_at`, a string.
- `cache_hit`, a boolean.

If a route returns data matching this model, FastAPI can serialize it into JSON.

### Type Hints

Type hints document what kind of value a variable, function argument, or return value should have:

```python
def _validate_driver_behaviour_payload(collection_scope: str, data: list[dict]) -> int:
```

This tells you:

- `collection_scope` should be a `str`.
- `data` should be a `list` of `dict` objects.
- The function returns an `int`.

Python does not enforce all type hints by itself at runtime, but they make code easier to understand and help editors catch mistakes.

### Private Helper Functions

Python does not have truly private functions in the same way some languages do. Instead, Python developers often use a leading underscore to signal "this is internal to this module."

Examples:

```python
def _normalize_driver_behaviour_hash_data(raw_data: list[dict]) -> list[dict]:
    ...

def _build_driver_behaviour_cache_key(collection_scope: str, raw_data: list[dict]) -> str:
    ...
```

These helpers support the public function `generate_driver_behaviour_summary()`. They are still callable, but the naming convention tells other developers not to treat them as the main public API.

### Decorators

A decorator adds behavior to a function. FastAPI uses decorators to register routes:

```python
@app.post("/ai/fleet-summary", response_model=FleetSummary)
def summarize_fleet(payload: FleetSummaryRequest):
    ...
```

The `@app.post(...)` line tells FastAPI that this function should run when an HTTP `POST` request arrives at `/ai/fleet-summary`.

### Exceptions

Exceptions are Python's way to signal that something went wrong.

The API layer catches expected and unexpected errors:

```python
try:
    return generate_fleet_summary(payload.collection_scope, collection_data)
except ValueError as error:
    raise HTTPException(status_code=400, detail=str(error)) from error
except Exception as error:
    logger.exception("Failed to generate fleet summary")
    raise HTTPException(status_code=500, detail="Internal server error") from error
```

This means:

- A `ValueError` becomes an HTTP 400 response because the client likely sent bad input.
- Any other unexpected exception is logged and becomes an HTTP 500 response.

### Dictionaries

Much of the project passes normalized event data around as dictionaries:

```python
{
    "driver_id": 312870,
    "journey_count": 7,
    "risk_profile": {
        "risk_level": "medium",
        "assessment_confidence": "low",
    },
}
```

Dictionaries are flexible, but they can become hard to reason about if too many layers change them. This project uses Pydantic models at the API boundary and normalization helpers inside the pipeline to keep dictionary data more predictable.

## Driver Behaviour Summary Walkthrough

The driver behaviour endpoint is the most important flow to understand because it shows the full design: API validation, deterministic normalization, cache lookup, risk scoring, AI narrative generation, and response construction.

The endpoint is:

```text
POST /ai/driver-behaviour-summary
```

The route function is `api/api.py::summarize_driver_behaviour()`, and the main pipeline function is `services/summary_pipeline.py::generate_driver_behaviour_summary()`.

### Step 1: FastAPI Receives The Request

The request body is validated against `DriverBehaviourSummaryRequest`:

```python
class DriverBehaviourSummaryRequest(BaseModel):
    collection_scope: str
    data: list[DriverBehaviourEventRecord] = Field(min_length=1)
```

This catches basic shape problems. For example, `data` must exist and must contain at least one row.

### Step 2: The API Converts Models To Dictionaries

Inside the route, each Pydantic row is converted to a plain dictionary:

```python
collection_data = [event.model_dump() for event in payload.data]
```

The pipeline works mostly with dictionaries, so this line bridges the model layer and service layer.

### Step 3: The Pipeline Validates Business Rules

`generate_driver_behaviour_summary()` starts by calling `_validate_driver_behaviour_payload()`:

```python
driver_id = _validate_driver_behaviour_payload(collection_scope, data)
```

This validation is more specific than Pydantic validation. It checks rules such as:

- `collection_scope` must be a non-empty string.
- `data` must be a non-empty list.
- Every row must have a valid positive `driverId`.
- All rows must belong to exactly one driver.
- `startTime` and `endTime` must be valid timestamps.

This separation is useful. Pydantic checks the basic data shape, while the pipeline checks business meaning.

### Step 4: The Pipeline Normalizes Data For Caching

The function `_normalize_driver_behaviour_hash_data()` creates stable rows for cache-key generation:

```python
normalized_data = _normalize_driver_behaviour_hash_data(data)
```

It keeps only fields that matter for driver behaviour summaries. It also coerces numeric strings into integers and sorts rows so equivalent payloads produce the same cache key even if the input order changes.

A simplified example:

```python
raw = [
    {"id": "2", "driverId": "312870", "dsmSeatbeltCount": "1"},
    {"id": 1, "driverId": 312870, "dsmSeatbeltCount": 0},
]

normalized = [
    {"id": 1, "driverId": 312870, "dsmSeatbeltCount": 0},
    {"id": 2, "driverId": 312870, "dsmSeatbeltCount": 1},
]
```

The real normalized rows contain more fields, but this shows the idea: stable type conversion and stable ordering.

### Step 5: The Pipeline Builds And Checks A Cache Key

The cache key is built from:

- `CACHE_SCHEMA_VERSION`
- `collection_scope`
- normalized row data

The simplified shape is:

```python
hash_source = {
    "version": CACHE_SCHEMA_VERSION,
    "collection_scope": collection_scope,
    "data": normalized_data,
}
```

`cache/cache_worker.py::build_driver_behaviour_cache_key()` serializes this source and returns a SHA256 digest. The cache file path then becomes:

```text
cache/driver_behaviour/{sha256}.json
```

If `load_driver_behaviour_cache_entry(cache_key)` returns a cache entry, the pipeline immediately returns a `DriverBehaviourSummary` with `cached=True`. That avoids repeated risk processing and AI calls.

### Step 6: The Risk Engine Builds Deterministic Risk Data

On a cache miss, the pipeline calls `_aggregate_driver_behaviour_payload()`:

```python
risk_profile = DriverRiskEngine.build_risk_profile(normalized_data)
behaviour_breakdown = DriverRiskEngine.compute_behaviour_breakdown(normalized_data)
```

The risk engine counts relevant behaviours and calculates a profile like this:

```python
{
    "model_version": "v1",
    "risk_level": "high",
    "risk_score": 5.5,
    "assessment_confidence": "medium",
    "primary_concerns": ["fatigue", "distraction", "seatbelt"],
    "requires_intervention": True,
}
```

This is deterministic. The same normalized input produces the same risk profile.

### Step 7: The Pipeline Either Skips AI Or Calls AI

If the event count is zero, the pipeline returns a static summary:

```python
if aggregated_payload["event_count"] <= 0:
    summary = _build_zero_event_driver_behaviour_summary(aggregated_payload)
```

This avoids paying for an AI call when there is nothing meaningful to summarize.

If there are events, the pipeline calls:

```python
summary = generate_driver_behaviour_aggregated_summary(aggregated_payload)
```

That function lives in `services/ai_summary.py`. It sanitizes the payload and asks OpenAI to write a narrative summary using only the deterministic risk data supplied by the backend.

### Step 8: The Pipeline Stores And Returns The Result

The pipeline writes a cache entry:

```python
cache_entry = {
    "cache_key": cache_key,
    "cache_version": CACHE_SCHEMA_VERSION,
    "generated_at": "...",
    "driver_id": aggregated_payload["driver_id"],
    "event_count": aggregated_payload["event_count"],
    "summary": summary,
}
```

Then it returns:

```python
DriverBehaviourSummary(
    cached=False,
    cache_key=cache_key,
    driver_id=cache_entry["driver_id"],
    event_count=cache_entry["event_count"],
    summary=cache_entry["summary"],
)
```

The response tells the caller whether the result came from cache, which driver was summarized, how many events were counted, and what summary text was generated.

## Fleet Summary Walkthrough

The fleet summary endpoint answers a different question from the driver behaviour endpoint.

Driver behaviour summary asks:

```text
What risk patterns are visible for this one driver?
```

Fleet summary asks:

```text
What operational safety patterns are visible across this fleet dataset?
```

The endpoint is:

```text
POST /ai/fleet-summary
```

The route function is `api/api.py::summarize_fleet()`, and the main pipeline function is `services/summary_pipeline.py::generate_fleet_summary()`.

### Step 1: FastAPI Validates The Request Shape

Fleet requests use `FleetSummaryRequest`:

```python
class FleetSummaryRequest(BaseModel):
    collection_scope: str
    data: list[FleetSummaryEventRecord] = Field(min_length=1)
```

Each row is a `FleetSummaryEventRecord`, which extends `BaseEventRecord` and requires an `id`.

### Step 2: The Pipeline Validates Required Inputs

`generate_fleet_summary()` starts with simple semantic validation:

```python
if not isinstance(collection_scope, str) or not collection_scope.strip():
    raise HTTPException(status_code=400, detail="Missing required field: collection_scope")

if not isinstance(data, list) or not data:
    raise HTTPException(status_code=400, detail="Missing required field: data")
```

This protects the rest of the function from empty or invalid inputs.

### Step 3: Fleet Rows Are Normalized

Fleet normalization uses the shared helper `normalize_summary_dataset()`:

```python
normalized_data = normalize_summary_dataset(
    data,
    int_fields=FLEET_SUMMARY_INT_FIELDS,
    text_fields=FLEET_SUMMARY_TEXT_FIELDS,
    text_defaults={
        "fleetLevelName": "unknown",
        "entityName": "unknown",
        "vrn": "",
    },
    sort_keys=("id", "fleetLevelId", "entityName"),
)
```

This makes fleet cache behavior predictable. Numeric fields become integers, text fields are stripped, missing text gets defaults, and rows are sorted.

### Step 4: The Pipeline Checks The Fleet Cache

Fleet cache keys look different from driver behaviour cache keys:

```text
fleet_summary:{sha256}
```

The key is built by `cache/cache_worker.py::build_fleet_summary_cache_key()`.

The pipeline then checks:

```python
cached_entry = get_fleet_summary_cache(cache_key)
```

`get_fleet_summary_cache()` applies TTL expiry. By default, fleet cache entries expire after one hour unless `FLEET_SUMMARY_CACHE_TTL_SECONDS` changes that setting.

### Step 5: The AI Layer Generates Fleet Narrative On Cache Miss

If there is no valid cache entry, the pipeline calls:

```python
summary = generate_fleet_summary_text(normalized_data)
```

That function lives in `services/ai_summary.py`.

Before prompting OpenAI, it sanitizes the dataset with `_sanitize_fleet_summary_prompt_data()`. The prompt asks for a fleet-level operational summary, top outliers, common event types, anomalies, and one operational action focus.

The fleet flow does not call `DriverRiskEngine`. It relies on the AI narrative layer to summarize the fleet-level dataset, while the driver behaviour endpoint uses deterministic risk scoring for one driver.

### Step 6: The Pipeline Stores And Returns The Fleet Summary

The pipeline stores the new result:

```python
cache_entry = set_fleet_summary_cache(cache_key, {"summary": summary})
```

`set_fleet_summary_cache()` adds metadata such as `cache_key` and `generated_at`.

The final response looks like:

```python
FleetSummary(
    summary=cache_entry.get("summary", "No summary available."),
    generated_at=cache_entry.get("generated_at", ""),
    cache_hit=False,
)
```

A cached response uses the same model, but returns `cache_hit=True`.

### Example Request Shape

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

### Example Response Shape

```json
{
  "summary": "Fleet-level operational summary text...",
  "generated_at": "2026-05-08T12:30:00Z",
  "cache_hit": false
}
```

## Key Design Decisions

### Risk Scoring Is Deterministic Python Code

Driver behaviour risk is calculated by `services/risk/driver_risk_engine.py::DriverRiskEngine`, not by OpenAI.

That design is important because risk scoring should be:

- Repeatable: the same input should produce the same score.
- Testable: tests can verify exact scores and risk levels.
- Auditable: a developer can read the weights and thresholds.
- Controlled: changing the risk model requires changing code, not prompt wording.

The core idea is visible in `calculate_weighted_risk_score()`:

```python
risk_score = weighted_event_sum / max(journey_count, 1)
```

The weighted sum uses journey presence counts. That means a category counts once per journey where it appears, rather than letting many repeated events in one journey dominate the score.

Risk bands are then deterministic:

```python
if score < 1.0:
    return "low"
if score < 3.0:
    return "medium"
return "high"
```

Those thresholds are tested in `tests/services/test_driver_risk_engine.py`.

### AI Writes Narrative, It Does Not Own The Risk Model

`services/ai_summary.py::generate_driver_behaviour_aggregated_summary()` receives an already-built payload containing `risk_profile` and `behaviour_summary`.

The prompt explicitly tells the AI:

- Do not infer severity from raw event counts.
- Do not compute or override risk scoring.
- Do not introduce behavioural categories not present in input.
- Only use the provided `risk_profile` and `behaviour_summary` fields.

This makes OpenAI a communication layer rather than the source of business truth.

That is a strong design choice for safety-related systems. The AI can phrase the result in clear language, but the backend decides what the risk actually is.

### Cache Keys Are Built From Normalized Data

The project does not cache using raw request JSON. Instead, it normalizes data first.

For driver behaviour summaries, `services/summary_pipeline.py::_normalize_driver_behaviour_hash_data()` keeps stable relevant fields, coerces numeric values, and sorts rows. Then `_build_driver_behaviour_cache_key()` includes:

```python
{
    "version": CACHE_SCHEMA_VERSION,
    "collection_scope": collection_scope,
    "data": normalized_data,
}
```

This prevents avoidable cache misses.

For example, these two values should mean the same thing:

```python
{"driverId": "312870", "dsmSeatbeltCount": "1"}
{"driverId": 312870, "dsmSeatbeltCount": 1}
```

Normalization helps both produce the same cache key.

### The API Layer Is Thin

`api/api.py` mostly receives requests, delegates to services, and handles HTTP errors.

That makes the route functions easier to read and test. The complicated behavior sits in `services/summary_pipeline.py`, where it can be tested without running a web server.

### Zero-Event Flows Skip AI

The project avoids AI calls when there are no tracked safety events.

Driver behaviour summaries use `services/summary_pipeline.py::_build_zero_event_driver_behaviour_summary()`. Collection summaries use `services/ai_summary.py::_is_zero_event_collection()` and `_build_zero_event_collection_summary()`.

This is practical for three reasons:

- It saves cost.
- It avoids unnecessary network calls.
- It produces a predictable summary for a simple case.

### Tests Protect Design Intent

The tests do more than check happy paths.

For example:

- `tests/services/test_driver_risk_engine.py` proves risk scoring uses journey presence rather than raw event totals.
- `tests/services/test_ai_summary.py` proves prompt-injection-like fields are removed before prompt construction.
- `tests/services/test_summary_pipeline.py` proves cache keys are stable across row ordering and numeric string/int variants.
- `tests/cache/test_cache_worker.py` proves invalid cache keys are rejected.

These tests document the design in executable form. When a future change breaks one of these rules, the test suite should catch it.

## Areas For Improvement

This section is not a criticism of the project. It is a learning map: these are places where a new developer can see realistic tradeoffs and future cleanup opportunities.

### Align `README.md` And `main.py`

`README.md` says the CLI flow prints a JSON list of generated driver summaries. `main.py::main()` currently prints:

```python
print("Fleet AI service is available. Please refer to the README.")
```

That mismatch can confuse a new developer. Either the README should describe `main.py` as a simple status entry point, or `main.py` should be expanded to run the documented CLI behavior.

### Align Docker Ports

`Dockerfile` exposes port `8000` and starts Uvicorn on port `8000`:

```dockerfile
EXPOSE 8000
CMD ["uvicorn", "api.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

`docker-compose.yml` maps:

```yaml
ports:
  - "87:80"
```

That maps host port `87` to container port `80`, but the app inside the container listens on `8000`. The compose file likely needs to map to `8000`, or the container command needs to listen on `80`.

### Use Logging Consistently

`api/api.py` uses structured logging:

```python
logger.exception("Failed to generate fleet summary")
```

`services/ai_summary.py` currently uses `print(...)` in exception handlers:

```python
print(f"Error generating fleet summary: {e}")
```

Using `logging.getLogger(__name__)` in `services/ai_summary.py` would make error handling more consistent and easier to observe in production.

### Avoid Import-Time OpenAI Client Creation

`services/ai_summary.py` creates the OpenAI client at module import time:

```python
load_dotenv()
client = OpenAI()
```

This is simple, but it couples importing the module to environment configuration. A future improvement would be to create the client through a helper function or dependency injection boundary. That would make tests and local development more flexible.

### Split The Pipeline Module If It Grows

`services/summary_pipeline.py` currently contains active driver behaviour flow, active fleet flow, and older journey/collection helper flows.

That is manageable now, but it could become hard to navigate. If more endpoints are added, consider splitting it into focused modules such as:

- `services/driver_behaviour_pipeline.py`
- `services/fleet_summary_pipeline.py`
- `services/journey_summary_pipeline.py`

This would make ownership clearer for new developers.

### Clarify Active Versus Legacy Flows

`api/api.py` exposes:

- `/ai/driver-behaviour-summary`
- `/ai/fleet-summary`

But `models/driver_summary.py` and `services/summary_pipeline.py` also contain older or currently unexposed concepts such as `DriverCollectionSummaryRequest`, `DriverJourneySummaryRequest`, `generate_event_collection_summary()`, and `generate_single_summary()`.

The project would be easier to understand if the documentation clearly labelled which flows are active API features and which are legacy/internal support paths.

### Consider More Typed Internal Payloads

The API boundary uses Pydantic models, but deeper pipeline functions often pass dictionaries.

That is normal in small Python services, but as the project grows, internal Pydantic models or dataclasses could make payload contracts clearer. For example, the aggregated driver behaviour payload could become a typed model instead of a plain dictionary.

### Add A Visual Sequence Diagram

This guide uses text diagrams, but a real sequence diagram would help beginners see the request flow:

```text
Client -> FastAPI -> Pipeline -> Cache
                         |
                         v
                    Risk Engine
                         |
                         v
                    AI Summary
```

Adding this to the README or this guide would make onboarding easier.

### Centralize Event Field Definitions

Event field names such as `adasEventsCount`, `dsmSeatbeltCount`, and `dsmFatigueCount` appear in several files:

- `models/driver_summary.py`
- `services/summary_pipeline.py`
- `services/ai_summary.py`
- `services/risk/driver_risk_engine.py`

This is understandable because different layers need the fields, but repeated field lists can drift over time. A future improvement could centralize shared event field definitions while still keeping risk weights inside `DriverRiskEngine`.
