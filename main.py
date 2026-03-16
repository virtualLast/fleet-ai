import json

from services.summary_pipeline import generate_summaries


def main():

    summaries = generate_summaries("events.json")

    print(json.dumps([s.model_dump() for s in summaries], indent=2))


if __name__ == "__main__":
    main()