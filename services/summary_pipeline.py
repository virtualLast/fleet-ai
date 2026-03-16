from models.driver_metrics import DriverMetrics
from models.driver_summary import DriverSummary
from util.data_loader import load_events
from services.driver_metrics import extract_driver_metrics
from services.summary_service import get_driver_summary
from cache.cache_worker import load_cache, save_cache
from fastapi import HTTPException


def generate_summaries(events_file):
    """
    Generate summaries for drivers based on events data.

    :param events_file: Path to the events JSON file.
    :return: List of driver summaries.
    """

    events = load_events(events_file)

    driver_metrics = [
        DriverMetrics(**extract_driver_metrics(driver))
        for driver in events
    ]

    cache = load_cache()

    summaries = []

    for driver in driver_metrics:

        summary = get_driver_summary(cache, driver)

        summaries.append(DriverSummary(
            journey_id=driver.id,
            driver=driver.name,
            summary=summary
        ))

    save_cache(cache)

    return summaries

def generate_single_summary(events_file, journey_id):
    """
    Generate a summary for a single journey based on the provided events file and journey ID.

    This function processes events data to extract and compute a summary for a specific driver
    and journey identified by the given journey ID. It interacts with cached records to generate
    the driver summary and updates the cache with the results.

    :param events_file: Path to the file containing event data. The data is expected to be in a
                        format that `load_events` can process.
    :type events_file: str
    :param journey_id: Unique identifier of the journey for which the summary is generated.
    :type journey_id: int
    :return: If successful, returns a dictionary containing the journey ID, driver's name, and
             the generated summary. If the journey ID is not found, returns an error dictionary
             indicating that the journey was not found.
    :rtype: dict
    """

    events = load_events(events_file)
    cache = load_cache()

    for event in events:

        if event["id"] == journey_id:

            driver_data = extract_driver_metrics(event)
            driver = DriverMetrics(**driver_data)

            summary = get_driver_summary(cache, driver)

            save_cache(cache)

            return DriverSummary(
                journey_id=driver.id,
                driver=driver.name,
                summary=summary
            )

    raise HTTPException(status_code=404, detail="Journey not found")