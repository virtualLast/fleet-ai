from models.driver_metrics import DriverMetrics
from services.ai_summary import generate_summary
from cache.cache_worker import get_cached_summary, store_summary


def has_events(driver: DriverMetrics):
    return any(getattr(driver, event) for event in [
        "forward_collision",
        "following_distance",
        "pedestrian_collision",
        "fatigue",
        "distraction",
        "phone_use",
        "yawning",
        "smoking",
        "seatbelt"
    ])


def get_driver_summary(cache, driver:DriverMetrics):

    journey_id = driver.id

    # Cache check
    summary = get_cached_summary(cache, journey_id)
    if summary:
        return summary

    # Zero-event guard
    if not has_events(driver):

        summary = "No safety events were recorded during this journey."

        store_summary(
            cache,
            journey_id,
            driver.name,
            summary
        )

        return summary

    # AI generation
    summary = generate_summary(driver.model_dump())

    store_summary(
        cache,
        journey_id,
        driver.name,
        summary
    )

    return summary