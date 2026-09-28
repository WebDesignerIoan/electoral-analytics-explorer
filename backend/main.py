import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Find the project root regardless of where the backend is started from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Processed race-level data produced by the analysis pipeline.
RACES_FILE = PROJECT_ROOT / "data" / "processed" / "senate_2022.json"


app = FastAPI(title="Electoral Analytics API")

# The React frontend runs on a different local origin
# (localhost:5173), so CORS must explicitly allow it to access the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/races")
def get_races():
    # Read the processed JSON file into a Python list of dictionaries.
    with RACES_FILE.open(encoding="utf-8") as file:
        races = json.load(file)

    # FastAPI automatically serializes the Python data back to JSON
    # when sending the response to the frontend.
    return races
