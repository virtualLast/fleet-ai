from fastapi import FastAPI
from services.summary_pipeline import generate_summaries, generate_single_summary
import json

app = FastAPI()

@app.get("/ai/driver-summaries")
def summarize():
    return generate_summaries('events.json')

@app.get("/ai/driver-summaries/{id}")
def summarize_journey(id: int):
    return generate_single_summary('events.json', id)