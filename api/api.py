"""HTTP API routes for fleet safety summaries.

This module keeps endpoint functions intentionally thin and delegates business
logic to `services.summary_pipeline`.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.summary_pipeline import generate_single_summary, generate_event_collection_summary
from models.driver_summary import (
    DriverSummary,
    DriverCollectionSummaryRequest,
    DriverCollectionSummary,
    DriverJourneySummaryRequest,
)

# FastAPI application object used by Uvicorn (`uvicorn api.api:app`).
app = FastAPI()

# Restrict browser access to known frontend origin(s).
origins = [
    "https://gen2portal.app.local",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/ai/driver-summary", response_model=DriverCollectionSummary)
def summarize_collection(payload: DriverCollectionSummaryRequest):
    """Generate one summary for an entire collection payload."""

    # Convert validated Pydantic objects into plain dicts expected by pipeline normalization.
    collection_data = [driver.model_dump() for driver in payload.data]

    return generate_event_collection_summary(payload.collection_scope, collection_data)


@app.post("/ai/driver-summary/{id}", response_model=DriverSummary)
def summarize_journey(id: int, payload: DriverJourneySummaryRequest | None = None):
    """Generate a summary for a single journey id with optional fallback payload context."""

    if payload is None:
        return generate_single_summary('events.json', id)

    return generate_single_summary('events.json', id, payload.model_dump())