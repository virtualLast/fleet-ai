from services import summary_pipeline


def _row(**overrides):
    """Build a deterministic canonical row for cache-key determinism tests."""
    base = {
        "id": 1,
        "driverId": 900,
        "entityName": "Driver Cache",
        "startTime": "2026-05-01T09:00:00Z",
        "endTime": "2026-05-01T09:30:00Z",
        "startAddress": "Alpha Road",
        "endAddress": "Beta Road",
        "adasEventsCount": 1,
        "dsmFatigueCount": 0,
        "dsmDistractionCount": 0,
        "dsmHandheldDevicesCount": 0,
        "dsmSeatbeltCount": 1,
        "dsmSmokingCount": 0,
    }
    base.update(overrides)
    return base


def test_identical_semantic_payloads_produce_identical_cache_keys():
    """What: Verify equivalent payloads produce identical driver-behaviour cache keys.

    Why: Semantically identical inputs must hit cache consistently.
    How: Build two equivalent datasets and compare generated keys.
    """
    data_a = [_row(id=1), _row(id=2, startTime="2026-05-02T09:00:00Z", endTime="2026-05-02T09:30:00Z")]
    data_b = [_row(id=1), _row(id=2, startTime="2026-05-02T09:00:00Z", endTime="2026-05-02T09:30:00Z")]

    key_a = summary_pipeline._build_driver_behaviour_cache_key("scope-a", data_a)
    key_b = summary_pipeline._build_driver_behaviour_cache_key("scope-a", data_b)

    assert key_a == key_b


def test_row_order_does_not_affect_cache_key():
    """What: Verify input row ordering does not alter cache key generation.

    Why: Collection order variance should not fragment cache entries.
    How: Compute keys for reversed row order and assert equality.
    """
    row_1 = _row(id=11, startTime="2026-05-01T06:00:00Z", endTime="2026-05-01T06:20:00Z")
    row_2 = _row(id=12, startTime="2026-05-01T08:00:00Z", endTime="2026-05-01T08:30:00Z")

    key_a = summary_pipeline._build_driver_behaviour_cache_key("scope-a", [row_1, row_2])
    key_b = summary_pipeline._build_driver_behaviour_cache_key("scope-a", [row_2, row_1])

    assert key_a == key_b


def test_irrelevant_address_and_text_changes_do_not_affect_cache_key():
    """What: Verify non-behavioural text changes do not affect cache keys.

    Why: Cache identity should depend on behavioural metrics, not incidental labels.
    How: Change addresses/name only and assert stable key output.
    """
    base = _row()
    changed = _row(startAddress="Completely Different Address", endAddress="Another Address", entityName="Renamed Driver")

    key_a = summary_pipeline._build_driver_behaviour_cache_key("scope-a", [base])
    key_b = summary_pipeline._build_driver_behaviour_cache_key("scope-a", [changed])

    assert key_a == key_b


def test_relevant_behaviour_changes_affect_cache_key():
    """What: Verify behavioural metric changes invalidate prior cache key.

    Why: Key must reflect summary-significant behaviour differences.
    How: Modify event counters and assert generated keys differ.
    """
    base = _row(dsmSeatbeltCount=1, adasEventsCount=1)
    changed = _row(dsmSeatbeltCount=0, adasEventsCount=3)

    key_a = summary_pipeline._build_driver_behaviour_cache_key("scope-a", [base])
    key_b = summary_pipeline._build_driver_behaviour_cache_key("scope-a", [changed])

    assert key_a != key_b


def test_risk_model_version_changes_invalidate_cache_keys(monkeypatch):
    """What: Verify schema/model-version changes force cache-key invalidation.

    Why: Versioned keying prevents stale summaries after scoring model updates.
    How: Monkeypatch `CACHE_SCHEMA_VERSION` and assert key changes.
    """
    data = [_row()]

    original_version = summary_pipeline.CACHE_SCHEMA_VERSION
    key_before = summary_pipeline._build_driver_behaviour_cache_key("scope-a", data)

    monkeypatch.setattr(summary_pipeline, "CACHE_SCHEMA_VERSION", f"{original_version}-changed")
    key_after = summary_pipeline._build_driver_behaviour_cache_key("scope-a", data)

    assert key_before != key_after
