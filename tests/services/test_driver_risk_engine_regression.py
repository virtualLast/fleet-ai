import copy

from services.risk.driver_risk_engine import DriverRiskEngine


def _sample_rows() -> list[dict]:
    """Return a deterministic baseline dataset for risk-engine regression assertions."""
    return [
        {
            "adasEventsCount": 0,
            "dsmFatigueCount": 0,
            "dsmDistractionCount": 0,
            "dsmHandheldDevicesCount": 0,
            "dsmSeatbeltCount": 4,
            "dsmSmokingCount": 0,
        },
        {
            "adasEventsCount": 1,
            "dsmFatigueCount": 1,
            "dsmDistractionCount": 1,
            "dsmHandheldDevicesCount": 1,
            "dsmSeatbeltCount": 0,
            "dsmSmokingCount": 0,
        },
    ]


def test_risk_score_stability_for_identical_datasets():
    """What: Verify identical datasets produce stable risk profile outputs.

    Why: Deterministic scoring is required for reproducible summaries and cache behavior.
    How: Build profiles from original/deep-copied rows and compare core outputs.
    """
    rows = _sample_rows()

    profile_a = DriverRiskEngine.build_risk_profile(rows)
    profile_b = DriverRiskEngine.build_risk_profile(copy.deepcopy(rows))

    assert profile_a["risk_score"] == profile_b["risk_score"]
    assert profile_a["risk_level"] == profile_b["risk_level"]
    assert profile_a["confidence"] == profile_b["confidence"]


def test_behaviour_weighting_stability_high_severity_outweighs_low_severity_repetition():
    """What: Verify severity weighting outranks low-severity repetition volume.

    Why: Risk model should prioritize high-impact categories over repeated minor events.
    How: Compare profiles from seatbelt-heavy vs mixed high-severity datasets.
    """
    low_severity_repetition = [
        {
            "adasEventsCount": 0,
            "dsmFatigueCount": 0,
            "dsmDistractionCount": 0,
            "dsmHandheldDevicesCount": 0,
            "dsmSeatbeltCount": 20,
            "dsmSmokingCount": 0,
        }
        for _ in range(3)
    ]
    high_severity_mixed = [
        {
            "adasEventsCount": 1,
            "dsmFatigueCount": 1,
            "dsmDistractionCount": 1,
            "dsmHandheldDevicesCount": 1,
            "dsmSeatbeltCount": 0,
            "dsmSmokingCount": 0,
        }
        for _ in range(3)
    ]

    low_profile = DriverRiskEngine.build_risk_profile(low_severity_repetition)
    high_profile = DriverRiskEngine.build_risk_profile(high_severity_mixed)

    assert high_profile["risk_score"] > low_profile["risk_score"]
    assert high_profile["risk_level"] in {"medium", "high"}


def test_concentration_rule_stability_single_category_dominance_yields_low_confidence():
    """What: Verify single-category dominance yields low confidence classification.

    Why: Narrow behaviour concentration should be flagged as lower-confidence evidence.
    How: Build seatbelt-dominant dataset and assert confidence/concerns outputs.
    """
    dominant_single_category = [
        {
            "adasEventsCount": 0,
            "dsmFatigueCount": 0,
            "dsmDistractionCount": 0,
            "dsmHandheldDevicesCount": 0,
            "dsmSeatbeltCount": 10,
            "dsmSmokingCount": 0,
        },
        {
            "adasEventsCount": 0,
            "dsmFatigueCount": 0,
            "dsmDistractionCount": 0,
            "dsmHandheldDevicesCount": 0,
            "dsmSeatbeltCount": 8,
            "dsmSmokingCount": 0,
        },
    ]

    profile = DriverRiskEngine.build_risk_profile(dominant_single_category)

    assert profile["confidence"] == "low"
    assert profile["primary_concerns"] == ["seatbelt"]


def test_model_version_stability_matches_current_constant():
    """What: Verify generated profile includes the current risk model version constant.

    Why: Version tagging is required for traceability and cache invalidation logic.
    How: Build profile and assert populated `model_version` matches engine constant.
    """
    profile = DriverRiskEngine.build_risk_profile(_sample_rows())

    assert profile["model_version"]
    assert profile["model_version"] == DriverRiskEngine.RISK_MODEL_VERSION
