from services.risk.engine import RiskEngine


def test_risk_engine_build_assessment_returns_v2_assessment_with_dimensions():
    """What: Verify engine orchestrates extraction, dimensions, and classification end-to-end.

    Why: Consumers need one deterministic v2 entrypoint with first-class dimension outputs.
    How: Build mixed-risk rows and assert model version, dimensions, and explainability fields.
    """
    rows = [
        {
            "adasFcwCount": 5,
            "adasHmwCount": 1,
            "adasPcwCount": 0,
            "dsmFatigueCount": 4,
            "dsmNoDriverCount": 0,
            "dsmHandheldDevicesCount": 2,
            "dsmSmokingCount": 0,
            "dsmDistractionCount": 2,
            "dsmYawningCount": 1,
            "dsmSeatbeltCount": 1,
        },
        {
            "adasFcwCount": 0,
            "adasHmwCount": 0,
            "adasPcwCount": 1,
            "dsmFatigueCount": 1,
            "dsmNoDriverCount": 1,
            "dsmHandheldDevicesCount": 0,
            "dsmSmokingCount": 1,
            "dsmDistractionCount": 0,
            "dsmYawningCount": 0,
            "dsmSeatbeltCount": 0,
        },
    ]

    assessment = RiskEngine.build_assessment(rows)

    assert assessment.model_version == "v2"
    assert set(assessment.dimensions.keys()) == {"persistent_risk", "acute_risk", "breadth_risk"}
    assert "decision_driver_dimension" in assessment.explainability
    assert "selected_action" in assessment.intervention
