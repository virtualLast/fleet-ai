import pytest

from services import ai_summary
from tests.helpers.summary_semantic_assertions import (
    assert_behaviour_consistency,
    assert_forbidden_phrases,
    assert_preferred_phrases,
    assert_required_concepts,
    assert_required_phrases,
    assert_summary_consistent_with_risk_profile,
    assert_tones,
)


def _make_aggregated_payload(risk_profile: dict, behaviour_summary: dict, event_count: int = 3) -> dict:
    """Build deterministic aggregated payload fixtures for semantic summary tests."""
    return {
        "driver": "Driver Test",
        "journey_count": 3,
        "event_count": event_count,
        "risk_profile": risk_profile,
        "behaviour_summary": behaviour_summary,
    }


def _patch_ai_summary(monkeypatch, summary_text: str):
    """Patch AI client with deterministic response text for semantic assertions."""
    class FakeResponse:
        output_text = summary_text

    class FakeResponses:
        @staticmethod
        def create(**_kwargs):
            """Return deterministic mocked response for patched AI client calls."""
            return FakeResponse()

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr(ai_summary, "client", FakeClient())


@pytest.mark.semantic
def test_narrative_alignment_for_low_confidence_single_pattern(monkeypatch):
    """What: Verify low-confidence single-pattern outputs stay cautious and aligned.

    Why: Low-confidence risk profiles must avoid overconfident escalation language.
    How: Patch model output, generate summary, and assert required/forbidden semantic constraints.
    """
    output = "Seatbelt use is the primary concern in this limited pattern, so conclusions should remain cautious."
    _patch_ai_summary(monkeypatch, output)

    payload = _make_aggregated_payload(
        risk_profile={
            "risk_level": "low",
            "risk_score": 0.67,
            "assessment_confidence": "low",
            "primary_concerns": ["seatbelt"],
        },
        behaviour_summary={
            "seatbelt_events": 6,
            "fatigue_events": 0,
            "distraction_events": 0,
            "adas_events": 0,
        },
    )

    summary = ai_summary.generate_driver_behaviour_aggregated_summary(payload)

    assert_required_phrases(summary, ["seatbelt"])
    assert_required_concepts(summary, ["low_confidence_cautious", "single_pattern_acknowledged"])
    assert_forbidden_phrases(summary, ["dangerous driving", "high-risk behaviour", "aggressive driving"])
    assert_summary_consistent_with_risk_profile(summary, payload["risk_profile"])
    assert_behaviour_consistency(summary, payload["behaviour_summary"], ["fatigue", "distraction", "handheld_device", "smoking", "aggression"])
    assert_tones(summary, ["cautious"], ["critical", "urgent"])


@pytest.mark.semantic
def test_narrative_alignment_for_high_risk_multi_category(monkeypatch):
    """What: Verify high-risk multi-category outputs reflect strong coaching guidance.

    Why: High-confidence multi-risk profiles should acknowledge multiple concern domains.
    How: Patch output with multi-signal narrative and assert phrase/tone consistency checks.
    """
    output = "There are clear fatigue and distraction signals with handheld-device events; targeted coaching intervention is recommended."
    _patch_ai_summary(monkeypatch, output)

    payload = _make_aggregated_payload(
        risk_profile={
            "risk_level": "high",
            "risk_score": 4.3,
            "assessment_confidence": "high",
            "primary_concerns": ["fatigue", "distraction", "handheld_device"],
        },
        behaviour_summary={
            "seatbelt_events": 0,
            "fatigue_events": 5,
            "distraction_events": 4,
            "adas_events": 3,
        },
    )

    summary = ai_summary.generate_driver_behaviour_aggregated_summary(payload)

    assert_required_phrases(summary, ["fatigue", "distraction"])
    assert_required_concepts(summary, ["high_confidence_firm", "multi_risk_acknowledged"])
    assert_tones(summary, ["coaching"], ["disciplinary"])
    assert_behaviour_consistency(summary, payload["behaviour_summary"], ["smoking", "aggression"])
    assert not assert_preferred_phrases(summary, ["coaching", "intervention"])


@pytest.mark.semantic
def test_hallucination_prevention_for_clean_driver(monkeypatch):
    """What: Verify clean-driver narrative avoids hallucinated severe concerns.

    Why: No-signal profiles should remain reassuring and non-escalatory.
    How: Patch positive output and assert supportive tone with forbidden-risk phrase checks.
    """
    output = "Overall the pattern appears safe and reassuring with no significant concerns observed in this period."
    _patch_ai_summary(monkeypatch, output)

    payload = _make_aggregated_payload(
        risk_profile={
            "risk_level": "low",
            "risk_score": 0.0,
            "assessment_confidence": "low",
            "primary_concerns": [],
        },
        behaviour_summary={
            "seatbelt_events": 0,
            "fatigue_events": 0,
            "distraction_events": 0,
            "adas_events": 0,
        },
        event_count=1,
    )

    summary = ai_summary.generate_driver_behaviour_aggregated_summary(payload)

    assert_required_concepts(summary, ["positive_reassurance", "no_concerns"])
    assert_forbidden_phrases(summary, ["dangerous", "high-risk behaviour", "missing data risk", "urgent intervention"])
    assert_behaviour_consistency(summary, payload["behaviour_summary"], ["fatigue", "distraction", "handheld_device", "seatbelt", "smoking", "aggression"])
    assert_tones(summary, ["supportive"], ["critical", "urgent", "disciplinary"])


@pytest.mark.semantic
def test_no_semantic_scoring_escalation_for_low_risk_low_confidence(monkeypatch):
    """What: Verify semantic guards detect escalatory language for low-risk profiles.

    Why: Regression protection is needed against unsafe overstatement in generated text.
    How: Patch intentionally escalatory output and assert semantic validators raise errors.
    """
    output = "This pattern is dangerous and clearly indicates high-risk behaviour requiring urgent intervention."
    _patch_ai_summary(monkeypatch, output)

    payload = _make_aggregated_payload(
        risk_profile={
            "risk_level": "low",
            "risk_score": 0.4,
            "assessment_confidence": "low",
            "primary_concerns": ["seatbelt"],
        },
        behaviour_summary={
            "seatbelt_events": 4,
            "fatigue_events": 0,
            "distraction_events": 0,
            "adas_events": 0,
        },
    )

    summary = ai_summary.generate_driver_behaviour_aggregated_summary(payload)

    with pytest.raises(AssertionError):
        assert_summary_consistent_with_risk_profile(summary, payload["risk_profile"])
    with pytest.raises(AssertionError):
        assert_forbidden_phrases(summary, ["dangerous", "high-risk behaviour", "urgent intervention"]) 