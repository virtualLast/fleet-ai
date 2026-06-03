# Runtime Flow

This document explains how requests move through Fleet AI at runtime for the two active endpoints.

## 1) Driver Behaviour Summary Flow

Endpoint: `POST /ai/driver-behaviour-summary`

### 1.1 Entry and delegation

Route function: `api/api.py::summarize_driver_behaviour`

```python
@app.post("/ai/driver-behaviour-summary", response_model=DriverBehaviourSummary)
def summarize_driver_behaviour(payload: DriverBehaviourSummaryRequest):
    collection_data = [event.model_dump() for event in payload.data]
    return generate_driver_behaviour_summary(payload.collection_scope, collection_data)
```

The API layer is intentionally thin: validate request shape, transform model instances to dictionaries, delegate to pipeline.

### 1.2 Pipeline orchestration (cache-first)

Pipeline function: `services/summary_pipeline.py::generate_driver_behaviour_summary`

Main runtime sequence:

1. Validate semantic payload rules (`_validate_driver_behaviour_payload`).
2. Normalize deterministic hash data (`_normalize_driver_behaviour_hash_data`).
3. Build cache key (`_build_driver_behaviour_cache_key`).
4. Attempt cache read (`load_driver_behaviour_cache_entry`).
5. On miss, aggregate deterministic analysis payload (`_aggregate_driver_behaviour_payload`).
6. Generate summary text:
   - zero-event deterministic text (`_build_zero_event_driver_behaviour_summary`), or
   - AI narrative (`generate_driver_behaviour_aggregated_summary`).
7. Persist cache entry (`store_driver_behaviour_cache_entry`).
8. Return `DriverBehaviourSummary`.

### 1.3 Cache-hit branch example

```python
cached_entry = load_driver_behaviour_cache_entry(cache_key)
if cached_entry:
    return DriverBehaviourSummary(
        cached=True,
        cache_key=cache_key,
        driver_id=cached_driver_id,
        event_count=cached_event_count,
        summary=summary_text,
    )
```

### 1.4 Runtime sequence diagram (driver)

```text
Client
  -> API route (FastAPI)
  -> summary_pipeline.generate_driver_behaviour_summary
      -> validate + normalize + key
      -> cache.load_driver_behaviour_cache_entry
      -> [hit] return response
      -> [miss] deterministic analysis + risk
      -> [miss] AI summary generation (if non-zero events)
      -> cache.store_driver_behaviour_cache_entry
  -> API response
```

## 2) Fleet Summary Flow

Endpoint: `POST /ai/fleet-summary`

### 2.1 Entry and delegation

Route function: `api/api.py::summarize_fleet`

```python
@app.post("/ai/fleet-summary", response_model=FleetSummary)
def summarize_fleet(payload: FleetSummaryRequest):
    collection_data = [event.model_dump() for event in payload.data]
    return generate_fleet_summary(payload.collection_scope, collection_data)
```

### 2.2 Pipeline orchestration (cache-first)

Pipeline function: `services/summary_pipeline.py::generate_fleet_summary`

Main runtime sequence:

1. Validate required semantic fields (`collection_scope`, `data`).
2. Normalize rows via `normalize_summary_dataset(...)`.
3. Build key via `build_fleet_summary_cache_key`.
4. Attempt cache read via `get_fleet_summary_cache`.
5. On miss, build deterministic `fleet_analysis` structure.
6. Generate narrative via `generate_fleet_summary_text(normalized_data)`.
7. Persist envelope via `set_fleet_summary_cache`.
8. Return `FleetSummary` (`cache_hit=False` on misses).

### 2.3 Fleet cache envelope example

```python
cache_entry = set_fleet_summary_cache(cache_key, {
    "metadata": {
        "cache_key": cache_key,
        "cache_version": CACHE_SCHEMA_VERSION,
        "model": "gpt-5.4",
    },
    "analysis": fleet_analysis,
    "summary_payload": {"text": summary},
    "summary": summary,
})
```

### 2.4 Runtime sequence diagram (fleet)

```text
Client
  -> API route (FastAPI)
  -> summary_pipeline.generate_fleet_summary
      -> normalize + key
      -> cache.get_fleet_summary_cache
      -> [hit] return response
      -> [miss] fleet analysis + AI summary
      -> cache.set_fleet_summary_cache
  -> API response
```

## 3) Active vs Legacy Runtime Paths

- Active public routes are only the two endpoints above.
- `services/summary_pipeline.py` still includes `_normalize_collection_data()` as older collection-style support code used by tests, but fallback extractor helpers have been removed from the active module.
