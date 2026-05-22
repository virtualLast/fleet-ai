from services.risk.feature_extraction import HIGH_SEVERITY_EVENT_THRESHOLD, extract_risk_features


def test_extract_risk_features_computes_per_behaviour_metrics_and_globals():
    """What: Verify extraction computes deterministic behaviour and global metrics.

    Why: Dimension evaluators depend on complete feature vectors, not raw row parsing.
    How: Build mixed normalized rows and assert key per-behaviour and global outputs.
    """
    rows = [
        {
            "adasFcwCount": 2,
            "adasHmwCount": 0,
            "adasPcwCount": 1,
            "dsmFatigueCount": 3,
            "dsmNoDriverCount": 0,
            "dsmHandheldDevicesCount": 1,
            "dsmSmokingCount": 0,
            "dsmDistractionCount": 0,
            "dsmYawningCount": 2,
            "dsmSeatbeltCount": 0,
        },
        {
            "adasFcwCount": 0,
            "adasHmwCount": 1,
            "adasPcwCount": 0,
            "dsmFatigueCount": 0,
            "dsmNoDriverCount": 1,
            "dsmHandheldDevicesCount": 0,
            "dsmSmokingCount": 2,
            "dsmDistractionCount": 1,
            "dsmYawningCount": 0,
            "dsmSeatbeltCount": 1,
        },
    ]

    features = extract_risk_features(rows)

    assert features.journey_count == 2
    assert features.active_behaviour_count == 10
    assert features.high_severity_journey_count == 0

    fatigue = features.behaviour_metrics["dsm_fatigue"]
    assert fatigue.raw_event_count == 3
    assert fatigue.journey_presence_count == 1
    assert fatigue.journey_ratio == 0.5
    assert fatigue.max_single_journey_events == 3
    assert fatigue.weighted_score == 15.0


def test_extract_risk_features_tracks_high_severity_journey_count():
    """What: Verify high-severity journey counting uses configured threshold.

    Why: Acute dimension depends on deterministic severe-journey baseline signals.
    How: Provide rows at/under threshold and assert resulting severe journey counter.
    """
    rows = [
        {"dsmFatigueCount": HIGH_SEVERITY_EVENT_THRESHOLD},
        {"dsmFatigueCount": HIGH_SEVERITY_EVENT_THRESHOLD - 1},
        {"adasFcwCount": HIGH_SEVERITY_EVENT_THRESHOLD + 2},
    ]

    features = extract_risk_features(rows)

    assert features.journey_count == 3
    assert features.high_severity_journey_count == 2


def test_extract_risk_features_handles_empty_or_invalid_rows_deterministically():
    """What: Verify extractor handles empty/invalid rows without non-deterministic failure.

    Why: Pipeline may include malformed rows that must not break deterministic processing.
    How: Pass invalid entries and assert zero-safe metric outputs.
    """
    features = extract_risk_features([None, "bad", 123])

    assert features.journey_count == 0
    assert features.active_behaviour_count == 0
    assert features.high_severity_journey_count == 0
    assert all(metric.raw_event_count == 0 for metric in features.behaviour_metrics.values())
    assert all(metric.journey_ratio == 0.0 for metric in features.behaviour_metrics.values())
