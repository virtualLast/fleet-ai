from services.summary_service import get_driver_summary, has_events


def test_has_events_returns_false_for_zero_event_driver(sample_driver_metrics):
    """What: Verify `has_events` is false when all event counters are zero.

    Why: Zero-event journeys should not trigger AI summary generation.
    How: Use baseline fixture metrics and assert `has_events` returns false.
    """
    assert has_events(sample_driver_metrics) is False


def test_has_events_returns_true_when_any_event_present(sample_driver_metrics):
    """What: Verify `has_events` is true when at least one event is present.

    Why: Any non-zero safety signal should be treated as an eventful journey.
    How: Set one event counter on the fixture and assert positive detection.
    """
    sample_driver_metrics.fatigue = 1

    assert has_events(sample_driver_metrics) is True


def test_get_driver_summary_returns_cached_summary(monkeypatch, sample_driver_metrics):
    """What: Verify `get_driver_summary` returns cache hit values without AI calls.

    Why: Cache hits should avoid unnecessary model invocation and latency.
    How: Provide cache entry, monkeypatch generator, call service, and assert no AI usage.
    """
    cache = {
        str(sample_driver_metrics.id): {
            "driver": sample_driver_metrics.name,
            "summary": "Cached summary",
            "generated_at": "2026-05-05",
        }
    }

    called = {"ai": 0}

    def fake_generate_summary(_):
        """Track unexpected AI invocation during cache-hit path."""
        called["ai"] += 1
        return "Generated summary"

    monkeypatch.setattr("services.summary_service.generate_summary", fake_generate_summary)

    result = get_driver_summary(cache, sample_driver_metrics)

    assert result == "Cached summary"
    assert called["ai"] == 0


def test_get_driver_summary_returns_zero_event_message_and_stores(monkeypatch, sample_driver_metrics):
    """What: Verify zero-event journeys store and return deterministic fallback text.

    Why: Eventless journeys should bypass AI and still populate cache metadata.
    How: Call service with empty cache and baseline metrics, then assert response and cache write.
    """
    cache = {}
    called = {"ai": 0}

    def fake_generate_summary(_):
        """Track unexpected AI invocation during zero-event fallback path."""
        called["ai"] += 1
        return "Generated summary"

    monkeypatch.setattr("services.summary_service.generate_summary", fake_generate_summary)

    result = get_driver_summary(cache, sample_driver_metrics)

    assert result == "No safety events were recorded during this journey."
    assert called["ai"] == 0

    cache_entry = cache[str(sample_driver_metrics.id)]
    assert cache_entry["driver"] == sample_driver_metrics.name
    assert cache_entry["summary"] == result
    assert "generated_at" in cache_entry


def test_get_driver_summary_calls_ai_for_non_zero_events(monkeypatch, sample_driver_metrics):
    """What: Verify non-zero journeys invoke AI summary and cache the result.

    Why: Eventful journeys require generated narrative summaries.
    How: Set one event metric, monkeypatch generator, and assert returned/cache values.
    """
    sample_driver_metrics.phone_use = 2
    cache = {}

    def fake_generate_summary(driver):
        """Return deterministic text while asserting expected driver passthrough."""
        assert driver.id == sample_driver_metrics.id
        return "AI generated summary"

    monkeypatch.setattr("services.summary_service.generate_summary", fake_generate_summary)

    result = get_driver_summary(cache, sample_driver_metrics)

    assert result == "AI generated summary"

    cache_entry = cache[str(sample_driver_metrics.id)]
    assert cache_entry["driver"] == sample_driver_metrics.name
    assert cache_entry["summary"] == "AI generated summary"
    assert "generated_at" in cache_entry
