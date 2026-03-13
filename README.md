# Fleet AI - Driver Safety Analyst

Fleet AI is a Python-based utility designed for fleet managers to automatically analyze driver behavior and safety events. It processes raw event data, extracts key performance indicators (KPIs), and utilizes AI to generate concise, actionable safety insights for each driver.

## What it does

- **Event Processing**: Reads driver event logs from `events.json`.
- **Metrics Extraction**: Identifies critical safety events such as:
  - Forward/Pedestrian collisions
  - Following distance violations
  - Fatigue and distraction (yawning, phone use, smoking)
  - Seatbelt violations
- **AI-Powered Insights**: Uses OpenAI's GPT models to analyze metrics and generate human-readable safety summaries (max 60 words).
- **Efficient Caching**: Implements a local JSON cache (`cache/summary_cache.json`) to store generated summaries, reducing API costs and improving performance for recurring data.

## Project Structure

- `main.py`: The entry point of the application.
- `services/`: Core logic for metrics extraction and AI summary generation.
- `cache/`: Handles loading and saving of the local summary cache.
- `util/`: Helper functions for data loading.
- `events.json`: Sample input file containing driver event data.

## Setup and Installation

### Prerequisites

- Python 3.x
- An OpenAI API Key

### Installation

1. Clone the repository to your local machine.
2. Install the required dependencies:
   ```bash
   pip install openai
   ```
3. Set your OpenAI API key as an environment variable:
   ```bash
   export OPENAI_API_KEY='your-api-key-here'
   ```

## How to Use

1. Prepare your driver data in `events.json` following the expected format (see existing `events.json` for reference).
2. Run the main script:
   ```bash
   python main.py
   ```
3. The script will output the driver name followed by their AI-generated safety insight to the console.
4. Summaries are automatically cached in `cache/summary_cache.json`.

## Configuration

The AI model and parameters (like temperature) can be configured in `services/ai_summary.py`. Currently, it is set to use a GPT model to generate focused, two-sentence safety insights.
