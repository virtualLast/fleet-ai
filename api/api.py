"""HTTP API routes for fleet safety summaries.

This module keeps endpoint functions intentionally thin and delegates business
logic to `services.summary_pipeline`.
"""

import logging

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from services.summary_pipeline import generate_driver_behaviour_summary, generate_fleet_summary
from models.driver_summary import (
    DriverBehaviourSummary,
    DriverBehaviourSummaryRequest,
    FleetSummary,
    FleetSummaryRequest,
)


logger = logging.getLogger(__name__)

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

@app.post("/ai/driver-behaviour-summary", response_model=DriverBehaviourSummary)
def summarize_driver_behaviour(payload: DriverBehaviourSummaryRequest):
    """Generate one behaviour summary for a single-driver collection payload."""

    # Convert validated Pydantic objects into plain dicts expected by pipeline normalization.
    collection_data = [event.model_dump() for event in payload.data]

    try:
        return generate_driver_behaviour_summary(payload.collection_scope, collection_data)
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Failed to generate driver behaviour summary")
        raise HTTPException(status_code=500, detail="Internal server error") from error


@app.post("/ai/fleet-summary", response_model=FleetSummary)
def summarize_fleet(payload: FleetSummaryRequest):
    """Generate one aggregate fleet summary for a collection payload."""

    collection_data = [event.model_dump() for event in payload.data]

    try:
        return generate_fleet_summary(payload.collection_scope, collection_data)
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Failed to generate fleet summary")
        raise HTTPException(status_code=500, detail="Internal server error") from error