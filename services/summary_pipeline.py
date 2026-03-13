from util.data_loader import load_events
from services.driver_metrics import extract_driver_metrics
from services.summary_service import get_driver_summary
from cache.cache_worker import load_cache, save_cache


def generate_summaries(events_file):

    events = load_events(events_file)

    driver_metrics = [
        extract_driver_metrics(driver)
        for driver in events
    ]

    cache = load_cache()

    summaries = []

    for driver in driver_metrics:

        summary = get_driver_summary(cache, driver)

        summaries.append({
            "journey_id": driver["id"],
            "driver": driver["name"],
            "summary": summary
        })

    save_cache(cache)

    return summaries