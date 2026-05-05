"""Small utility helpers for loading JSON input data used by the pipeline."""

import json

# -----------------------------
# Load driver events from a JSON file
# -----------------------------
def load_events(filepath):
    """Load and return event rows from a JSON file path."""

    with open(filepath, "r") as f:
        events = json.load(f)

    return events