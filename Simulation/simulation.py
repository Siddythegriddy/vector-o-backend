# ================================================================
# Simulation/simulation.py
#
# Master Simulation & Lifecycle Engine
# ================================================================

import os
import sys
import json
import random

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from virus import DiseaseEngine
from Behavior.behavior import BehaviorEngine
from Simulation.Settlements import SettlementGenerator, SETTLEMENT_ALIASES
from Simulation.routine_network import SocialNetworkEngine, DailyRoutineGenerator
from risk_engine import RiskEngine
from Simulation import policy_engine


class SimulationEngine:
    def __init__(self, config=None):
        self.config = config or self._load_config()
        self.virus_data = self.config.get("virus", {})
        self.settlement_data = self.config.get("settlement", {})
        self.personalities = self.config.get("personalities", [])
        self.policy_config = self.config.get("policies", {})
        
        raw_type = self.settlement_data.get("type", "Suburban")
        self.settlement_type = SETTLEMENT_ALIASES.get(str(raw_type).strip().lower(), "Suburban")

        # Sub-Engines
        self.settlement_gen = SettlementGenerator(settlement_type=self.settlement_type)
        self.risk_engine = RiskEngine(settlement_type=self.settlement_type, alert_level="Yellow")
        self.behavior_engine = BehaviorEngine(self.virus_data, self.personalities, settlement_type=self.settlement_type)
        self.disease_engine = DiseaseEngine(self.virus_data)
        self.policy_engine = policy_engine.PolicyEngine()
        self.policy_engine.update_policies(self.policy_config)

        # State Variables
        self.agents = []
        self.nodes = {}
        self.social_graph = {}
        self.routine_engine = None
        self.agent_lookup = {}

    def _load_config(self):
        config_path = os.path.join(ROOT_DIR, "data", "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                return json.load(f)
        return {
            "days": 10,
            "initial_infections": 2,
            "virus": {"transmission": 35.0, "mortality": 2.0},
            "settlement": {"type": "Suburban"},
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

    def setup_simulation(self, initial_infections=2):
        self.agents = []
        agent_id_counter = 1
        for p in self.personalities:
            p_name = p.get("Name", "Default")
            pop_count = p.get("Population", 10)
            mask_prob = p.get("MaskProbability", 0.50)
            
            for _ in range(pop_count):
                age_val = 68 if p_name == "Cautious Senior" else (10 if p_name == "Children" else 35)
                occ_val = "Retired" if p_name == "Cautious Senior" else ("Student" if p_name == "Children" else "Office Worker")

                self.agents.append({
                    "id": agent_id_counter,
                    "personality": p_name,
                    "social_activity": p.get("Social", 5),
                    "mobility": p.get("Mobility", 5),
                    "mask_probability": mask_prob,
                    "health_state": "S",
                    "vaccinated": False,
                    "wearing_mask": False,
                    "risk_score": 0.0,
                    "stay_home": False,
                    "age": age_val,
                    "occupation": occ_val,
                    "mask_days_worn": 0
                })
                agent_id_counter += 1

        for i in range(min(initial_infections, len(self.agents))):
            self.agents[i]["health_state"] = "I"

        self.nodes = self.settlement_gen.generate_settlement_nodes(len(self.agents))
        self.agents = self.settlement_gen.assign_agents_to_settlement(self.agents, self.nodes)
        network_engine = SocialNetworkEngine(self.agents, self.nodes)
        self.social_graph = network_engine.build_network()
        self.routine_engine = DailyRoutineGenerator(self.agents)
        self.agent_lookup = {agent["id"]: agent for agent in self.agents}

    def apply_daily_mask_decisions(self):
        mask_mandate_active = self.policy_engine.active_policies.get("mask_rule", False)
        for agent in self.agents:
            base_prob = agent.get("mask_probability", 0.5)
            effective_prob = min(0.98, max(0.80, base_prob + 0.35)) if mask_mandate_active else base_prob
            wears_mask = random.random() < effective_prob
            agent["wearing_mask"] = wears_mask
            if wears_mask:
                agent["mask_days_worn"] += 1

    def get_personality_breakdown(self, total_days):
        personality_names = sorted(list(set(a["personality"] for a in self.agents)))
        breakdown = []
        for p_name in personality_names:
            group = [a for a in self.agents if a["personality"] == p_name]
            total = len(group)
            i_c = sum(1 for a in group if a["health_state"] == "I")
            actual_mask_days = sum(a["mask_days_worn"] for a in group)
            mask_pct = (actual_mask_days / (total * total_days) * 100) if (total * total_days) > 0 else 0.0
            breakdown.append({
                "cohort": p_name,
                "total": total,
                "infected": i_c,
                "mask_compliance_pct": round(mask_pct, 1)
            })
        return breakdown

    def generate_personality_routes_and_matrix(self, all_interaction_logs):
        """
        Calculates:
        1. 24-hour hour-by-hour routing trajectories per personality type.
        2. Pairwise cross-personality interaction matrix and metrics.
        3. City-type specific movement vectors and location flow summary.
        """
        personality_names = sorted(list(set(a["personality"] for a in self.agents)))
        
        # 1. 24-HOUR ROUTE MAP PER PERSONALITY
        personality_routes = {}
        for p_name in personality_names:
            group = [a for a in self.agents if a["personality"] == p_name]
            if not group:
                continue

            hourly_schedule = []
            for hour in range(24):
                loc_counts = {}
                zone_counts = {}
                sample_coords = []

                for agent in group:
                    # Simulate location for this hour
                    if agent.get("stay_home", False):
                        loc = agent.get("home_id", "home_1")
                    elif 0 <= hour < 8 or hour >= 21:
                        loc = agent.get("home_id", "home_1")
                    elif 8 <= hour < 17:
                        loc = agent.get("primary_day_location", agent.get("home_id", "home_1"))
                    else:
                        loc = agent.get("secondary_location", agent.get("home_id", "home_1"))

                    loc_counts[loc] = loc_counts.get(loc, 0) + 1
                    
                    node = self.nodes.get(loc, {})
                    loc_type = node.get("type", "home")
                    zone_counts[loc_type] = zone_counts.get(loc_type, 0) + 1
                    
                    pos = node.get("position", {"x": 50.0, "y": 50.0, "z": 0.0})
                    sample_coords.append(pos)

                # Determine dominant location type for this hour
                dominant_zone = max(zone_counts, key=zone_counts.get) if zone_counts else "home"
                avg_x = round(sum(p["x"] for p in sample_coords) / len(sample_coords), 2) if sample_coords else 50.0
                avg_y = round(sum(p["y"] for p in sample_coords) / len(sample_coords), 2) if sample_coords else 50.0

                time_label = f"{hour:02d}:00"
                phase_label = "Sleep/Home" if (0 <= hour < 8 or hour >= 21) else ("Work/School" if 8 <= hour < 17 else "Social/Market")

                hourly_schedule.append({
                    "hour": hour,
                    "time_label": time_label,
                    "phase": phase_label,
                    "dominant_zone": dominant_zone,
                    "location_distribution": zone_counts,
                    "center_point": {"x": avg_x, "y": avg_y}
                })

            # Key waypoint nodes visited by cohort
            home_nodes = list(set(a.get("home_id") for a in group if a.get("home_id")))
            day_nodes = list(set(a.get("primary_day_location") for a in group if a.get("primary_day_location")))
            social_nodes = list(set(a.get("secondary_location") for a in group if a.get("secondary_location")))

            personality_routes[p_name] = {
                "personality": p_name,
                "sample_size": len(group),
                "home_nodes": home_nodes,
                "day_nodes": day_nodes,
                "social_nodes": social_nodes,
                "hourly_trajectory": hourly_schedule
            }

        # 2. CROSS-PERSONALITY INTERACTION MATRIX
        interaction_matrix = {}
        for p1 in personality_names:
            interaction_matrix[p1] = {}
            for p2 in personality_names:
                interaction_matrix[p1][p2] = {
                    "total_contacts": 0,
                    "distance_sum": 0.0,
                    "transmission_attempts": 0,
                    "infections_passed": 0,
                    "locations": {}
                }

        for day_log in all_interaction_logs:
            for rec in day_log.get("records", []):
                p_a = rec["agent_a"]["personality"]
                p_b = rec["agent_b"]["personality"]
                dist = rec.get("distance", 1.5)
                loc = rec.get("location", "city")
                passed = rec.get("passed_on", False)
                attempted = rec.get("transmission_attempted", False)

                if p_a in interaction_matrix and p_b in interaction_matrix[p_a]:
                    cell = interaction_matrix[p_a][p_b]
                    cell["total_contacts"] += 1
                    cell["distance_sum"] += dist
                    if attempted:
                        cell["transmission_attempts"] += 1
                    if passed:
                        cell["infections_passed"] += 1
                    cell["locations"][loc] = cell["locations"].get(loc, 0) + 1

                if p_a != p_b and p_b in interaction_matrix and p_a in interaction_matrix[p_b]:
                    cell_rev = interaction_matrix[p_b][p_a]
                    cell_rev["total_contacts"] += 1
                    cell_rev["distance_sum"] += dist
                    if attempted:
                        cell_rev["transmission_attempts"] += 1
                    if passed:
                        cell_rev["infections_passed"] += 1
                    cell_rev["locations"][loc] = cell_rev["locations"].get(loc, 0) + 1

        # Format matrix results nicely
        formatted_matrix = []
        for p1 in personality_names:
            for p2 in personality_names:
                cell = interaction_matrix[p1][p2]
                contacts = cell["total_contacts"]
                avg_dist = round(cell["distance_sum"] / contacts, 2) if contacts > 0 else 0.0
                top_loc = max(cell["locations"], key=cell["locations"].get) if cell["locations"] else "N/A"
                formatted_matrix.append({
                    "personality_a": p1,
                    "personality_b": p2,
                    "total_contacts": contacts,
                    "avg_distance": avg_dist,
                    "transmission_attempts": cell["transmission_attempts"],
                    "infections_passed": cell["infections_passed"],
                    "primary_contact_location": top_loc
                })

        # 3. CITY-TYPE ROUTE PATHWAYS
        city_type_routes = {
            "settlement_type": self.settlement_type,
            "description": f"Spatial node mobility pathways across {self.settlement_type} layout.",
            "zones_available": list(set(n.get("type") for n in self.nodes.values())),
            "personality_pathways": {
                p_name: {
                    "routine": f"Home ({len(data['home_nodes'])} nodes) ➔ Day ({len(data['day_nodes'])} nodes) ➔ Social ({len(data['social_nodes'])} nodes) ➔ Home",
                    "primary_nodes": data["day_nodes"],
                    "social_nodes": data["social_nodes"]
                }
                for p_name, data in personality_routes.items()
            }
        }

        return personality_routes, formatted_matrix, city_type_routes

    def update_agent_coordinates(self):
        """Calculates 2D/3D spatial coordinates for each agent based on assigned node + jitter."""
        for agent in self.agents:
            # If hospitalized, force agent location to hospital node
            if agent.get("hospitalized", False):
                agent["current_location"] = agent.get("hospital_id", "hospital_1")

            loc_id = agent.get("current_location", "home_1")
            node = self.nodes.get(loc_id)
            if node:
                pos = node.get("position", {"x": 50.0, "y": 50.0, "z": 0.0})
                offset_x = random.uniform(-2.5, 2.5)
                offset_y = random.uniform(-2.5, 2.5)
                agent["x"] = round(pos["x"] + offset_x, 2)
                agent["y"] = round(pos["y"] + offset_y, 2)
                agent["z"] = pos.get("z", 0.0)
            else:
                agent["x"] = round(random.uniform(5.0, 95.0), 2)
                agent["y"] = round(random.uniform(5.0, 95.0), 2)
                agent["z"] = 0.0

    def run_simulation(self):
        total_days = self.config.get("days", 10)
        initial_infections = self.config.get("initial_infections", 2)
        self.setup_simulation(initial_infections=initial_infections)

        daily_curve = []
        all_interaction_logs = []

        for day in range(1, total_days + 1):
            active_cases = sum(1 for a in self.agents if a["health_state"] == "I")
            hospitalized_cases = sum(1 for a in self.agents if a.get("hospitalized", False))
            self.agents = self.risk_engine.evaluate_daily_population_risk(self.agents, active_cases, len(self.agents))

            for agent in self.agents:
                self.behavior_engine.decide_behaviour(agent)
            self.agents = self.policy_engine.apply_morning_policies(self.agents, self.risk_engine)
            self.apply_daily_mask_decisions()

            daily_interactions_count = 0
            day_interaction_records = []

            for hour in range(24):
                self.routine_engine.update_agent_positions(hour)
                if self.policy_engine.active_policies["curfew"]:
                    for agent in self.agents:
                        self.policy_engine.enforce_hourly_curfew(agent, hour)

                self.update_agent_coordinates()

                if 8 <= hour <= 20:
                    hourly_interactions = self.behavior_engine.simulate_grid_interactions(self.agents)
                    daily_interactions_count += len(hourly_interactions)
                    newly_exposed, interaction_records = self.disease_engine.process_interactions(hourly_interactions, self.agent_lookup)
                    
                    for rec in interaction_records:
                        rec["day"] = day
                        rec["hour"] = hour
                        day_interaction_records.append(rec)

            self.disease_engine.update_agent_health_states(self.agents)
            self.update_agent_coordinates()

            # Trigger mutation check
            mutated, msg = self.disease_engine.check_for_mutation(active_cases)

            s_c = sum(1 for a in self.agents if a["health_state"] == "S")
            e_c = sum(1 for a in self.agents if a["health_state"] == "E")
            i_c = sum(1 for a in self.agents if a["health_state"] == "I")
            r_c = sum(1 for a in self.agents if a["health_state"] == "R")
            d_c = sum(1 for a in self.agents if a["health_state"] == "D")
            h_c = sum(1 for a in self.agents if a.get("hospitalized", False))

            daily_curve.append({
                "day": day,
                "susceptible": s_c,
                "exposed": e_c,
                "infected": i_c,
                "recovered": r_c,
                "deceased": d_c,
                "hospitalized": h_c,
                "interactions": daily_interactions_count
            })

            all_interaction_logs.append({
                "day": day,
                "interactions_count": len(day_interaction_records),
                "records": day_interaction_records
            })

        personality_routes, cross_personality_matrix, city_type_routes = self.generate_personality_routes_and_matrix(all_interaction_logs)

        return {
            "status": "success",
            "settlement": self.settlement_type,
            "population": len(self.agents),
            "city_nodes": self.nodes,
            "agents": [
                {
                    "id": a["id"],
                    "personality": a.get("personality", ""),
                    "health_state": a.get("health_state", "S"),
                    "hospitalized": a.get("hospitalized", False),
                    "wearing_mask": a.get("wearing_mask", False),
                    "social_distancing": a.get("social_distancing", False) or a.get("stay_home", False),
                    "risk_score": a.get("risk_score", 0.0),
                    "position": {"x": a.get("x", 0.0), "y": a.get("y", 0.0), "z": a.get("z", 0.0)},
                    "current_location": a.get("current_location", ""),
                    "home_id": a.get("home_id", ""),
                    "primary_day_location": a.get("primary_day_location", ""),
                    "secondary_location": a.get("secondary_location", ""),
                    "age": a.get("age", 30),
                    "occupation": a.get("occupation", "")
                }
                for a in self.agents
            ],
            "daily_curve": daily_curve,
            "personality_breakdown": self.get_personality_breakdown(total_days),
            "personality_routes": personality_routes,
            "cross_personality_matrix": cross_personality_matrix,
            "city_type_routes": city_type_routes,
            "interaction_logs": all_interaction_logs
        }


def run_engine(config_dict: dict) -> dict:
    """Entrypoint function called by server.py / API endpoints."""
    engine = SimulationEngine(config=config_dict)
    return engine.run_simulation()


if __name__ == "__main__":
    engine = SimulationEngine()
    results = engine.run_simulation()
    print(f"Simulation completed: {results['population']} agents over {len(results['daily_curve'])} days.")