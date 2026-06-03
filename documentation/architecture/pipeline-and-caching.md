# Pipeline and Caching

This document explains how Fleet AI orchestrates request processing, normalization, deterministic analysis, and cache persistence.

## 1) Pipeline Responsibilities

Primary module: `services/summary_pipeline.py`

### Driver behaviour orchestration

`generate_driver_behaviour_summary(collection_scope, data)` performs:

1. semantic validation (`_validate_driver_behaviour_payload`),
2. deterministic normalization for cache hashing (`_normalize_driver_behaviour_hash_data`),
3. deterministic key build (`_build_driver_behaviour_cache_key`),
4. cache read (`load_driver_behaviour_cache_entry`),
5. on miss: deterministic aggregation (`_aggregate_driver_behaviour_payload`),
6. summary generation (zero-event deterministic fallback or AI narrative),
7. cache write (`store_driver_behaviour_cache_entry`),
8. response mapping to `DriverBehaviourSummary`.

### Fleet orchestration

`generate_fleet_summary(collection_scope, data)` performs:

1. required semantic validation,
2. shared normalization using `normalize_summary_dataset`,
3. fleet key build (`build_fleet_summary_cache_key`),
4. cache read (`get_fleet_summary_cache`),
5. on miss: deterministic `fleet_analysis` construction,
6. AI narrative generation (`generate_fleet_summary_text`),
7. cache write (`set_fleet_summary_cache`),
8. response mapping to `FleetSummary`.

## 2) Deterministic Normalization

### Driver behaviour hash normalization

The driver hash path keeps only relevant fields and uses stable type coercion + sort order. This ensures payloads with equivalent meaning produce the same cache key.

Example concept:

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

### Shared fleet normalization

Fleet normalization uses `util/summary_normalization.py::normalize_summary_dataset`:

- selected integer fields are coerced via `safe_int`,
- selected text fields are coerced via `safe_text`,
- rows are deterministically sorted when `sort_keys` are provided.

## 3) Cache Keys

## 3.1 Driver behaviour cache key

Built from:

- `CACHE_SCHEMA_VERSION`,
- `collection_scope`,
- normalized hash data.

The key is generated via `cache/cache_worker.py::build_driver_behaviour_cache_key` and persisted under driver cache storage.

## 3.2 Fleet cache key

Built via `cache/cache_worker.py::build_fleet_summary_cache_key(collection_scope, normalized_data)`.

Key shape:

```text
fleet_summary:{sha256}
```

## 4) Cache Entry Envelopes

## 4.1 Driver cache envelope (current shape)

```python
cache_entry = {
    "cache_version": CACHE_SCHEMA_VERSION,
    "metadata": {
        "cache_key": cache_key,
        "cache_version": CACHE_SCHEMA_VERSION,
        "generated_at": "...",
        "model": "gpt-5.4",
        "driver_id": aggregated_payload["driver_id"],
    },
    "analysis": {
        "driver_id": aggregated_payload["driver_id"],
        **aggregated_payload["analysis"],
    },
    "summary": summary,
    "summary_payload": {"text": summary},
    "driver_id": aggregated_payload["driver_id"],
    "event_count": aggregated_payload["event_count"],
}
```

Important: response assembly supports both nested and legacy top-level summary shapes when reading cache.

## 4.2 Fleet cache envelope (current shape)

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

## 5) Fleet TTL Behavior

`cache/cache_worker.py::get_fleet_summary_cache` enforces TTL expiry for fleet cache entries.

- Default TTL is controlled by `FLEET_SUMMARY_CACHE_TTL_SECONDS`.
- Expired entries are treated as cache misses.

## 6) Why This Design Matters

- Deterministic normalization and keying reduce avoidable cache misses.
- Cache-first orchestration reduces AI cost/latency.
- Structured `analysis` + `summary_payload` improves traceability for downstream consumers.
- Backward-compatible cache reads reduce migration risk while payload shapes evolve.