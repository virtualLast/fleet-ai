"""CLI entry point for generating per-driver safety summaries from `events.json`."""

import json

from services.summary_pipeline import generate_summaries


def main():
    """Run the summary pipeline and print serializable output for shell consumption."""

    # Generate typed `DriverSummary` models from the local events dataset.
    summaries = generate_summaries("events.json")

    # Convert models to dictionaries before pretty-printing JSON.
    print(json.dumps([s.model_dump() for s in summaries], indent=2))


if __name__ == "__main__":
    main()