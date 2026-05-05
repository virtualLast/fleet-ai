from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.summary_pipeline import generate_summaries, generate_single_summary
from models.driver_summary import DriverSummary

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

@app.get("/ai/driver-summaries", response_model=List[DriverSummary])
def summarize():
    return generate_summaries('events.json')

@app.get("/ai/driver-summaries/{id}", response_model=DriverSummary)
def summarize_journey(id: int):
    return generate_single_summary('events.json', id)