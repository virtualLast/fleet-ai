from typing import List
from fastapi import FastAPI
from services.summary_pipeline import generate_summaries, generate_single_summary
from models.driver_summary import DriverSummary

app = FastAPI()

@app.get("/ai/driver-summaries", response_model=List[DriverSummary])
def summarize():
    return generate_summaries('events.json')

@app.get("/ai/driver-summaries/{id}", response_model=DriverSummary)
def summarize_journey(id: int):
    return generate_single_summary('events.json', id)