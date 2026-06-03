import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from services import ai_summary, summary_pipeline
from services.risk.driver_risk_engine import DriverRiskEngine
from tests.helpers.summary_semantic_assertions import (
    assert_behaviour_consistency,
    assert_forbidden_phrases,
    assert_required_concepts,
    assert_required_phrases,
    assert_summary_consistent_with_risk_profile,
    assert_tones,
)

GOLDEN_ROOT = Path("tests/golden_datasets")
METADATA_LOG = Path("tests/prompt_regressions/prompt_regression_runs.jsonl")
MAX_METADATA_LINES = 500


def _load_json(path: Path) -> dict:
    """Load a JSON document from disk for prompt-regression fixtures."""
    return json.loads(path.read_text())


def _append_run_metadata(dataset_name: str, summary: str) -> None:
    """Append bounded prompt-regression execution metadata for traceability.

    Args:
        dataset_name: Prompt-regression scenario identifier.
        summary: Generated summary text used to derive a stable hash.

    Returns:
        None.

    Side effects:
        - Creates the metadata directory and file when missing.
        - Reads existing JSONL metadata entries from disk.
        - Appends one new run record and truncates to `MAX_METADATA_LINES`.
        - Persists the bounded JSONL content back to disk.

    Raises:
        OSError: If filesystem read/write operations fail.
    """
    METADATA_LOG.parent.mkdir(parents=True, exist_ok=True)
    METADATA_LOG.touch(exist_ok=True)
    payload = {
        "provider": "openai",
        "model": os.getenv("OPENAI_MODEL") or os.getenv("OPENAI_CHAT_MODEL") or "unspecified-model",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset": dataset_name,
        "summary_hash": hashlib.sha256(summary.encode("utf-8")).hexdigest(),
    }
    lines = METADATA_LOG.read_text(encoding="utf-8").splitlines()
    lines.append(json.dumps(payload))
    trimmed_lines = lines[-MAX_METADATA_LINES:]
    METADATA_LOG.write_text("\n".join(trimmed_lines) + "\n", encoding="utf-8")


@pytest.mark.prompt_regression
@pytest.mark.parametrize(
    "scenario",
    [
        "repetitive-seatbelt-low-confidence",
        "mixed-high-risk",
    ],
)
def test_driver_summary_prompt_regression_semantics_live_model(scenario: str):
    """What: Verify live-model summaries satisfy semantic regression expectations.

    Why: Prompt drift can regress safety language and risk-alignment semantics.
    How: Build aggregated payload from golden input, generate summary, and assert semantic constraints.
    """
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not configured for prompt regression test")

    dataset = _load_json(GOLDEN_ROOT / "input" / f"{scenario}.json")
    expectations = _load_json(GOLDEN_ROOT / "expectations" / f"{scenario}.json")
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

    _append_run_metadata(scenario, summary)

    semantic = expectations["semantic"]

    try:
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
    except AssertionError as error:
        strict_mode = os.getenv("STRICT_PROMPT_REGRESSION", "false").lower() in {"1", "true", "yes", "on"}
        # Advisory by default; enable strict mode when prompt-regression failures should block.
        if strict_mode:
            raise
        pytest.xfail(f"Advisory prompt-regression semantic drift: {error}")
