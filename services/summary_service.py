"""Driver-level summary orchestration with cache-first behavior."""

from typing import Any

from cache.cache_worker import get_cached_summary, store_summary
from models.driver_metrics import DriverMetrics
from services.ai_summary import generate_summary


def has_events(driver: DriverMetrics) -> bool:
    """Return `True` when at least one tracked safety counter is non-zero."""

    return any(
        getattr(driver, event)
        for event in [
            "forward_collision",
            "following_distance",
            "pedestrian_collision",
            "fatigue",
            "distraction",
            "phone_use",
            "yawning",
            "smoking",
            "seatbelt",
        ]
    )


def get_driver_summary(cache: dict[str, Any], driver: DriverMetrics) -> str:
    """Return a journey summary using cache-first and zero-event shortcuts.

    Flow:
    1. Return cached summary when available.
    2. For zero-event journeys, return deterministic fallback text (no AI call).
    3. Otherwise generate summary via AI and persist to cache.
    """

    journey_id = driver.id

    # Cache check
    summary = get_cached_summary(cache, journey_id)
    if summary:
        return summary

    # Zero-event guard
    if not has_events(driver):
        summary = "No safety events were recorded during this journey."

        store_summary(cache, journey_id, driver.name, summary)

        return summary

    # AI generation
    summary = generate_summary(driver)

    store_summary(cache, journey_id, driver.name, summary)

    return summary
