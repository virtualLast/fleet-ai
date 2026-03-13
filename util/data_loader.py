import json

# -----------------------------
# Load driver events from a JSON file
# -----------------------------
def load_events(filepath):

    with open(filepath, "r") as f:
        events = json.load(f)

    return events