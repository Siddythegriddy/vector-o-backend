# api/main.py

import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import os

app = FastAPI(title="Epidemic Simulator API")

# Enable CORS so Lovable can talk to your backend without browser security blocks
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust to Lovable app URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request Data Models ---
class VirusData(BaseModel):
    name: str = "COVID-Variant"
    transmission: float = 35.0
    mortality: float = 2.0
    mutation: float = 10.0
    incubation: int = 5
    recovery: int = 14
    immune_escape: float = 15.0

class SettlementConfig(BaseModel):
    type: str = "Suburban"  # "Metropolis", "Suburban", "Rural Village", "Enclosed Facility"
    custom_capacity: int = 30

class PersonalityData(BaseModel):
    Name: str
    Population: int
    Age: str = "18-50"
    Social: int = 5
    Mask: str = "Sometimes"
    Vaccine: str = "Delayed"
    Mobility: int = 5
    Isolation: int = 50
    Description: str = ""

class SimulationConfigPayload(BaseModel):
    virus: VirusData
    settlement: SettlementConfig = SettlementConfig()
    personalities: List[PersonalityData]

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"status": "Simulator Backend Running"}

@app.post("/api/configure")
def update_configuration(payload: SimulationConfigPayload):
    """
    Endpoint called by Lovable UI to submit virus, settlement, and population setup.
    Saves directly to data/config.json.
    """
    try:
        # Calculate total population
        total_pop = sum(p.Population for p in payload.personalities)
        
        config_dict = {
            "virus": payload.virus.dict(),
            "settlement": payload.settlement.dict(),
            "personalities": [p.dict() for p in payload.personalities],
            "total_population": total_pop
        }

        # Determine target file path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        config_path = os.path.join(data_dir, "config.json")

        # Save payload to config.json
        with open(config_path, "w") as f:
            json.dump(config_dict, f, indent=4)

        return {
            "success": True, 
            "message": "Configuration saved to data/config.json",
            "total_population": total_pop,
            "settlement_type": payload.settlement.type
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config")
def get_current_config():
    """Returns current data/config.json content."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "data", "config.json")
    
    if not os.path.exists(config_path):
        raise HTTPException(status_code=404, detail="Configuration not initialized yet.")
        
    with open(config_path, "r") as f:
        return json.load(f)

@app.get("/api/personality-routes")
def get_personality_routes(settlement_type: str = "Suburban", days: int = 5):
    """Returns mapped personality routes, cross-personality interactions, and city movement pathways."""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if base_dir not in sys.path:
            sys.path.append(base_dir)
        from Simulation.simulation import SimulationEngine
        config = {
            "days": days,
            "initial_infections": 2,
            "settlement": {"type": settlement_type},
            "virus": {"transmission": 35.0, "mortality": 2.0},
            "personalities": [
                {"Name": "Extrovert", "Population": 20, "Social": 8, "Mobility": 8, "MaskProbability": 0.50},
                {"Name": "Introvert", "Population": 15, "Social": 2, "Mobility": 3, "MaskProbability": 0.85},
                {"Name": "Cautious Senior", "Population": 10, "Social": 3, "Mobility": 2, "MaskProbability": 0.90},
                {"Name": "Essential Worker", "Population": 15, "Social": 6, "Mobility": 7, "MaskProbability": 0.65},
                {"Name": "Children", "Population": 15, "Social": 7, "Mobility": 5, "MaskProbability": 0.20},
                {"Name": "Travelers", "Population": 5, "Social": 9, "Mobility": 10, "MaskProbability": 0.25}
            ],
            "policies": {"mask_rule": False, "lockdown": False, "curfew": False}
        }
        engine = SimulationEngine(config=config)
        results = engine.run_simulation()
        return {
            "settlement": results["settlement"],
            "personality_routes": results["personality_routes"],
            "cross_personality_matrix": results["cross_personality_matrix"],
            "city_type_routes": results["city_type_routes"],
            "personality_breakdown": results["personality_breakdown"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


    from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or your Lovable preview origin
    allow_methods=["*"],
    allow_headers=["*"],
)
