from cache.cache_worker import (
    get_cached_summary,
    store_summary
)

from services.ai_summary import generate_summary

def get_driver_summary(cache, driver):
    """
    Gets a summary for a driver. 
    If the summary is not found in the cache, it generates a new summary and stores it in the cache.
    Args:
        driver (dict): A dictionary containing raw driver events.
    Returns:
        str: A summary for the driver.
        :param driver:
        :param cache:
    """
    journey_id = driver["id"]
    summary = get_cached_summary(cache, journey_id)

    if summary:
        return summary

    # 2. Generate AI summary
    summary = generate_summary(driver)

    # 3. Store result
    store_summary(
        cache,
        journey_id,
        driver["name"],
        summary
    )

    return summary