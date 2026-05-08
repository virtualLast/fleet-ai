from services.risk.driver_risk_engine import DriverRiskEngine


def test_compute_behaviour_breakdown_tracks_raw_counts_and_journey_presence():
    normalized_data = [
        {
            "adasEventsCount": 0,
            "dsmFatigueCount": 0,
            "dsmDistractionCount": 1,
            "dsmHandheldDevicesCount": 0,
            "dsmSeatbeltCount": 2,
            "dsmSmokingCount": 0,
        },
        {
            "adasEventsCount": 1,
            "dsmFatigueCount": 0,
            "dsmDistractionCount": 0,
            "dsmHandheldDevicesCount": 1,
            "dsmSeatbeltCount": 0,
            "dsmSmokingCount": 3,
        },
        {
            "adasEventsCount": 0,
            "dsmFatigueCount": 1,
            "dsmDistractionCount": 2,
            "dsmHandheldDevicesCount": 0,
            "dsmSeatbeltCount": 1,
            "dsmSmokingCount": 0,
        },
    ]

    breakdown = DriverRiskEngine.compute_behaviour_breakdown(normalized_data)

    assert breakdown["dsm_seatbelt"]["raw_event_count"] == 3
    assert breakdown["dsm_seatbelt"]["journey_presence_count"] == 2
    assert breakdown["dsm_distraction"]["raw_event_count"] == 3
    assert breakdown["dsm_distraction"]["journey_presence_count"] == 2
    assert breakdown["adas_events"]["raw_event_count"] == 1
    assert breakdown["adas_events"]["journey_presence_count"] == 1


def test_calculate_weighted_risk_score_uses_journey_presence_not_raw_event_totals():
    behaviour_breakdown = {
        "dsm_fatigue": {"raw_event_count": 0, "journey_presence_count": 0},
        "dsm_distraction": {"raw_event_count": 0, "journey_presence_count": 0},
        "dsm_handheld_device": {"raw_event_count": 0, "journey_presence_count": 0},
        "adas_events": {"raw_event_count": 0, "journey_presence_count": 0},
        "dsm_seatbelt": {"raw_event_count": 30, "journey_presence_count": 1},
        "dsm_smoking": {"raw_event_count": 0, "journey_presence_count": 0},
    }

    # If raw totals were used, this would be inflated. Presence-based score is 1.0.
    risk_score = DriverRiskEngine.calculate_weighted_risk_score(behaviour_breakdown, journey_count=2)

    assert risk_score == 1.0


def test_classify_risk_level_uses_expected_boundaries():
    assert DriverRiskEngine.classify_risk_level(0.9999) == "low"
    assert DriverRiskEngine.classify_risk_level(1.0) == "medium"
    assert DriverRiskEngine.classify_risk_level(2.9999) == "medium"
    assert DriverRiskEngine.classify_risk_level(3.0) == "high"


def test_compute_confidence_applies_single_signal_and_dominance_rules():
    single_signal_breakdown = {
        "dsm_fatigue": {"raw_event_count": 0, "journey_presence_count": 0},
        "dsm_distraction": {"raw_event_count": 0, "journey_presence_count": 0},
        "dsm_handheld_device": {"raw_event_count": 0, "journey_presence_count": 0},
        "adas_events": {"raw_event_count": 0, "journey_presence_count": 0},
        "dsm_seatbelt": {"raw_event_count": 10, "journey_presence_count": 4},
        "dsm_smoking": {"raw_event_count": 0, "journey_presence_count": 0},
    }
    dominant_signal_breakdown = {
        "dsm_fatigue": {"raw_event_count": 1, "journey_presence_count": 1},
        "dsm_distraction": {"raw_event_count": 0, "journey_presence_count": 0},
        "dsm_handheld_device": {"raw_event_count": 0, "journey_presence_count": 0},
        "adas_events": {"raw_event_count": 0, "journey_presence_count": 0},
        "dsm_seatbelt": {"raw_event_count": 100, "journey_presence_count": 5},
        "dsm_smoking": {"raw_event_count": 0, "journey_presence_count": 0},
    }

    assert DriverRiskEngine.compute_confidence(10, single_signal_breakdown) == "low"
    assert DriverRiskEngine.compute_confidence(10, dominant_signal_breakdown) == "low"


def test_compute_confidence_returns_medium_and_high_for_distribution_levels():
    medium_breakdown = {
        "dsm_fatigue": {"raw_event_count": 3, "journey_presence_count": 2},
        "dsm_distraction": {"raw_event_count": 2, "journey_presence_count": 2},
        "dsm_handheld_device": {"raw_event_count": 0, "journey_presence_count": 0},
        "adas_events": {"raw_event_count": 0, "journey_presence_count": 0},
        "dsm_seatbelt": {"raw_event_count": 4, "journey_presence_count": 3},
        "dsm_smoking": {"raw_event_count": 0, "journey_presence_count": 0},
    }
    high_breakdown = {
        "dsm_fatigue": {"raw_event_count": 2, "journey_presence_count": 2},
        "dsm_distraction": {"raw_event_count": 2, "journey_presence_count": 2},
        "dsm_handheld_device": {"raw_event_count": 2, "journey_presence_count": 2},
        "adas_events": {"raw_event_count": 2, "journey_presence_count": 2},
        "dsm_seatbelt": {"raw_event_count": 1, "journey_presence_count": 1},
        "dsm_smoking": {"raw_event_count": 1, "journey_presence_count": 1},
    }

    assert DriverRiskEngine.compute_confidence(8, medium_breakdown) == "medium"
    assert DriverRiskEngine.compute_confidence(10, high_breakdown) == "high"


def test_derive_primary_concerns_ranks_by_weighted_contribution_and_caps_to_three():
    behaviour_breakdown = {
        "dsm_fatigue": {"raw_event_count": 3, "journey_presence_count": 2},      # 15
        "dsm_distraction": {"raw_event_count": 4, "journey_presence_count": 3},   # 16
        "dsm_handheld_device": {"raw_event_count": 2, "journey_presence_count": 2},  # 8
        "adas_events": {"raw_event_count": 8, "journey_presence_count": 4},       # 24
        "dsm_seatbelt": {"raw_event_count": 10, "journey_presence_count": 5},     # 20
        "dsm_smoking": {"raw_event_count": 1, "journey_presence_count": 1},       # 2
    }

    concerns = DriverRiskEngine.derive_primary_concerns(behaviour_breakdown)

    assert concerns == ["adas", "seatbelt", "distraction"]
    assert len(concerns) == 3


def test_build_risk_profile_includes_model_version_and_deterministic_fields():
    normalized_data = [
        {
            "adasEventsCount": 1,
            "dsmFatigueCount": 1,
            "dsmDistractionCount": 1,
            "dsmHandheldDevicesCount": 1,
            "dsmSeatbeltCount": 1,
            "dsmSmokingCount": 1,
        },
        {
            "adasEventsCount": 2,
            "dsmFatigueCount": 2,
            "dsmDistractionCount": 1,
            "dsmHandheldDevicesCount": 1,
            "dsmSeatbeltCount": 1,
            "dsmSmokingCount": 1,
        },
    ]

    profile = DriverRiskEngine.build_risk_profile(normalized_data)

    assert profile["model_version"] == "v1"
    assert profile["risk_level"] == "high"
    assert profile["risk_score"] == 20.0
    assert profile["confidence"] == "high"
    assert profile["requires_intervention"] is True
    assert profile["primary_concerns"] == ["fatigue", "adas", "distraction"]
