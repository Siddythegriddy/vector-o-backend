# ==============================================================================
# server.py
#
# FastAPI Server Engine & Streaming API
# ==============================================================================

import os
import sys
import json
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Ensure root directory is on sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from Simulation.simulation import run_engine

app = FastAPI(title="Epidemic Simulator API", version="1.0.0")

# Complete CORS Configuration for Bolt / WebContainers / Localhost / Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    return {"status": "ok"}


# ==============================================================================
# DATA SCHEMAS (Flexibly handle both camelCase & snake_case inputs)
# ==============================================================================

class PolicyConfig(BaseModel):
    mask_rule: bool = False
    lockdown: bool = False
    curfew: bool = False
    social_distancing: bool = False

class VirusConfig(BaseModel):
    transmission: float = 35.0
    r0: Optional[float] = 3.5
    mortality: float = 2.0
    incubation: int = 5
    recovery: int = 14

class PersonalityItem(BaseModel):
    Name: str
    Population: int
    Social: int = 5
    Mobility: int = 5
    MaskProbability: float = 0.5

class SimulationRequest(BaseModel):
    days: int = 10
    total_days: Optional[int] = 10
    population: Optional[int] = 80
    initial_infections: int = 2
    settlement_type: Optional[str] = "Suburban"
    settlement: Optional[Dict[str, Any]] = None
    virus: Optional[VirusConfig] = Field(default_factory=VirusConfig)
    personalities: Optional[List[PersonalityItem]] = Field(default_factory=list)
    policies: Optional[PolicyConfig] = Field(default_factory=PolicyConfig)


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@app.get("/")
async def root():
    return {"status": "online", "message": "Epidemic Simulator Engine API"}


@app.post("/run-simulation")
async def execute_simulation(config: SimulationRequest):
    try:
        # Normalize incoming data so backend handles both raw JSON formats seamlessly
        payload = config.dict()
        
        # Ensure settlement dictionary exists for legacy simulation engine
        if not payload.get("settlement"):
            payload["settlement"] = {"type": payload.get("settlement_type") or "Suburban"}
            
        if payload.get("total_days"):
            payload["days"] = payload["total_days"]

        results = run_engine(payload)
        return results
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Simulation Engine Error: {str(err)}")


@app.post("/api/configure")
async def save_configuration(payload: SimulationRequest):
    try:
        data_dir = os.path.join(ROOT_DIR, "data")
        os.makedirs(data_dir, exist_ok=True)
        config_path = os.path.join(data_dir, "config.json")

        with open(config_path, "w") as f:
            json.dump(payload.dict(), f, indent=4)

        return {"success": True, "message": "Configuration saved to data/config.json"}
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@app.get("/api/config")
async def get_configuration():
    config_path = os.path.join(ROOT_DIR, "data", "config.json")
    if not os.path.exists(config_path):
        raise HTTPException(status_code=404, detail="Configuration not initialized.")
    with open(config_path, "r") as f:
        return json.load(f)


@app.get("/api/city-layout")
async def get_city_layout(settlement_type: str = "Suburban", population: int = 80):
    """Returns 2D/3D city layout nodes, building coordinates, height, and colors."""
    try:
        from Simulation.Settlements import SettlementGenerator
        gen = SettlementGenerator(settlement_type=settlement_type)
        nodes = gen.generate_settlement_nodes(population)
        return {
            "settlement_type": settlement_type,
            "population": population,
            "city_nodes": nodes
        }
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@app.get("/stream-simulation")
async def stream_simulation(days: int = 365, initial_infections: int = 2, settlement_type: str = "Suburban"):
    """
    Streams frame-by-frame simulation updates continuously until disconnected.
    Contains:
    - Day & hour progress
    - City nodes (3D buildings layout)
    - All agents with coordinates (x,y,z), infection state, mask status, social distancing, hospitalization
    - ALL agent interactions with pairwise infection data.
    """
    async def event_generator():
        try:
            config = {
                "days": days,
                "initial_infections": initial_infections,
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

            from Simulation.simulation import SimulationEngine
            engine = SimulationEngine(config=config)
            engine.setup_simulation(initial_infections=initial_infections)

            # First event: City Layout & Initial Agent Setup
            yield f"data: {json.dumps({'event': 'init', 'city_nodes': engine.nodes, 'population': len(engine.agents)})}\n\n"
            await asyncio.sleep(0.1)

            # Infinite simulation loop — streams until client stops/disconnects
            day = 1
            while True:
                active_cases = sum(1 for a in engine.agents if a["health_state"] == "I")
                engine.agents = engine.risk_engine.evaluate_daily_population_risk(engine.agents, active_cases, len(engine.agents))

                for agent in engine.agents:
                    engine.behavior_engine.decide_behaviour(agent)
                engine.agents = engine.policy_engine.apply_morning_policies(engine.agents, engine.risk_engine)
                engine.apply_daily_mask_decisions()

                for hour in range(8, 21):
                    engine.routine_engine.update_agent_positions(hour)
                    if engine.policy_engine.active_policies.get("curfew", False):
                        for agent in engine.agents:
                            engine.policy_engine.enforce_hourly_curfew(agent, hour)

                    engine.update_agent_coordinates()

                    hourly_interactions = engine.behavior_engine.simulate_grid_interactions(engine.agents)
                    newly_exposed, interaction_records = engine.disease_engine.process_interactions(hourly_interactions, engine.agent_lookup)

                    payload = {
                        "event": "frame",
                        "day": day,
                        "hour": hour,
                        "hospital_load": sum(1 for a in engine.agents if a.get("hospitalized", False)),
                        "city_stats": {
                            "susceptible": sum(1 for a in engine.agents if a["health_state"] == "S"),
                            "exposed": sum(1 for a in engine.agents if a["health_state"] == "E"),
                            "infected": sum(1 for a in engine.agents if a["health_state"] == "I"),
                            "recovered": sum(1 for a in engine.agents if a["health_state"] == "R"),
                            "deceased": sum(1 for a in engine.agents if a["health_state"] == "D")
                        },
                        "agents": [
                            {
                                "id": a["id"],
                                "health_state": a.get("health_state", "S"),
                                "hospitalized": a.get("hospitalized", False),
                                "wearing_mask": a.get("wearing_mask", False),
                                "social_distancing": a.get("social_distancing", False) or a.get("stay_home", False),
                                "risk_score": a.get("risk_score", 0.0),
                                "position": {"x": a.get("x", 0.0), "y": a.get("y", 0.0), "z": a.get("z", 0.0)},
                                "personality": a.get("personality", ""),
                                "occupation": a.get("occupation", ""),
                                "age": a.get("age", 30)
                            }
                            for a in engine.agents
                        ],
                        "interactions": interaction_records
                    }

                    yield f"data: {json.dumps(payload)}\n\n"
                    await asyncio.sleep(0.15)

                engine.disease_engine.update_agent_health_states(engine.agents)
                day += 1

        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
# ==============================================================================
# SERVER LAUNCHER
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Read environment PORT for Render/Cloud deployment compatibility
    port = int(os.environ.get("PORT", 8000))
    ngrok_token = os.getenv("NGROK_TOKEN")

    if ngrok_token and port == 8000:
        try:
            import ngrok
            listener = ngrok.forward(8000, authtoken=ngrok_token)
            print(f"🚀 Public URL: {listener.url()}")
        except Exception as e:
            print(f"⚠️ Ngrok launch failed: {e}")

    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)