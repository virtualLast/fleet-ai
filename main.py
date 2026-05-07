"""CLI entry point for generating per-driver safety summaries from `events.json`."""

import json

from services.summary_pipeline import generate_summaries


def main():
    """Print a simple status message when this module is run directly."""

    print("Fleet AI service is available. Please refer to the README.")

if __name__ == "__main__":
    main()