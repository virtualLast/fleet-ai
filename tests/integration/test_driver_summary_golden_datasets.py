import json
from pathlib import Path

import pytest

from services import ai_summary, summary_pipeline
from services.risk.driver_risk_engine import DriverRiskEngine
from tests.helpers.summary_semantic_assertions import (
    assert_behaviour_consistency,
    assert_forbidden_phrases,
    assert_preferred_phrases,
    assert_required_concepts,
    assert_required_phrases,
    assert_summary_consistent_with_risk_profile,
    assert_tones,
)


GOLDEN_ROOT = Path("tests/golden_datasets")


def _load_json(path: Path) -> dict:
    """Load a golden dataset or expectation JSON fixture from disk."""
    return json.loads(path.read_text())


def _patch_summary_output(monkeypatch, summary_text: str):
    """Patch AI client with deterministic summary text for integration assertions."""
    class FakeResponse:
        output_text = summary_text

    class FakeResponses:
        @staticmethod
        def create(**_kwargs):
            """Return deterministic fake response for mocked AI calls."""
            return FakeResponse()

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr(ai_summary, "client", FakeClient())


@pytest.mark.integration
@pytest.mark.parametrize(
    ("scenario", "mocked_summary"),
    [
        (
            "repetitive-seatbelt-low-confidence",
            "Seatbelt is the main issue in a limited single-pattern dataset, so conclusions should stay cautious.",
        ),
        (
            "mixed-high-risk",
            "Clear fatigue and distraction patterns with handheld-device use indicate a high-risk profile and justify coaching intervention.",
        ),
        (
            "clean-driver-no-events",
            "Safe and reassuring behaviour with no significant concerns observed.",
        ),
    ],
)
def test_driver_summary_golden_dataset_flow(monkeypatch, scenario: str, mocked_summary: str):
    """What: Validate full driver-summary flow against golden datasets.

    Why: Integration coverage ensures scoring and semantic assertions stay stable across scenarios.
    How: Load golden input/expectations, run pipeline+summary path with patched model output, and assert risk/semantic checks.
    """
    dataset = _load_json(GOLDEN_ROOT / "input" / f"{scenario}.json")
    expectations = _load_json(GOLDEN_ROOT / "expectations" / f"{scenario}.json")

    _patch_summary_output(monkeypatch, mocked_summary)

    rows = dataset["data"]
    normalized_rows = summary_pipeline._normalize_driver_behaviour_hash_data(rows)
    breakdown = DriverRiskEngine.compute_behaviour_breakdown(normalized_rows)
    risk_profile = DriverRiskEngine.build_risk_profile(normalized_rows)
    behaviour_summary = summary_pipeline._build_behaviour_summary_from_breakdown(breakdown)
    event_count = sum(summary_pipeline._calculate_behaviour_row_event_count(row) for row in rows)

    summary = ai_summary.generate_driver_behaviour_aggregated_summary(
        {
            "driver": rows[0].get("entityName", "unknown") if rows else "unknown",
            "journey_count": len(rows),
            "event_count": event_count,
            "risk_profile": risk_profile,
            "behaviour_summary": behaviour_summary,
        }
    )

    risk_expectation = expectations["risk"]
    if "risk_level" in risk_expectation:
        assert risk_profile["risk_level"] == risk_expectation["risk_level"]
    if "risk_level_allowed" in risk_expectation:
        assert risk_profile["risk_level"] in set(risk_expectation["risk_level_allowed"])
    if "confidence" in risk_expectation:
        assert risk_profile["confidence"] == risk_expectation["confidence"]

    for concern in risk_expectation.get("primary_concerns_contains", []):
        assert concern in risk_profile["primary_concerns"]
    if risk_expectation.get("primary_concerns_empty"):
        assert not risk_profile["primary_concerns"]

    semantic = expectations["semantic"]
    assert_required_phrases(summary, semantic.get("required", []))
    assert_forbidden_phrases(summary, semantic.get("forbidden", []))
    assert_required_concepts(summary, semantic.get("required_concepts", []))
    assert_summary_consistent_with_risk_profile(summary, risk_profile)
    assert_behaviour_consistency(
        summary,
        behaviour_summary,
        semantic.get("forbidden_behaviour_mentions_when_absent", []),
    )
    assert_tones(summary, semantic.get("required_tones", []), semantic.get("forbidden_tones", []))

    # Preferred terms are advisory signal only and intentionally not hard-fail.
    _ = assert_preferred_phrases(summary, semantic.get("preferred", []))
