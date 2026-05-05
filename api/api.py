from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.summary_pipeline import generate_single_summary, generate_event_collection_summary
from models.driver_summary import DriverSummary, DriverCollectionSummaryRequest, DriverCollectionSummary

app = FastAPI()

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
    collection_data = [driver.model_dump() for driver in payload.data]

    return generate_event_collection_summary(payload.collection_scope, collection_data)

@app.get("/ai/driver-summary/{id}", response_model=DriverSummary)
def summarize_journey(id: int):
    return generate_single_summary('events.json', id)