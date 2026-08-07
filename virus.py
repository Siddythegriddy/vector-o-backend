# ================================================================
# virus/disease.py
#
# Phase 6: Disease Engine & Transmission Dynamics
#
# Handles:
#   1. SEIR/D State Transitions: Susceptible -> Exposed -> Infected -> Recovered/Deceased
#   2. Transmission Probability Calculation (Masks, Vaccines, Viral Load)
#   3. Incubation & Recovery Timers
#   4. Mutation & Immune Escape Scaling
# ================================================================

import random


class DiseaseEngine:
    def __init__(self, virus_data):
        """
        Initializes viral characteristics from config.
        """
        self.virus = virus_data
        self.name = virus_data.get("name", "COVID-Variant")
        
        # Normalize percentages (e.g., 35.0 -> 0.35)
        self.base_transmission = float(virus_data.get("transmission", 35.0)) / 100.0
        self.mortality_rate = float(virus_data.get("mortality", 2.0)) / 100.0
        self.mutation_rate = float(virus_data.get("mutation", 10.0)) / 100.0
        self.immune_escape = float(virus_data.get("immune_escape", 15.0)) / 100.0
        
        self.incubation_period = int(virus_data.get("incubation", 5))
        self.recovery_period = int(virus_data.get("recovery", 14))

    # ============================================================
    # 1. TRANSMISSION EVALUATION (INTERACTIONS -> EXPOSURE)
    # ============================================================

    def process_interactions(self, interactions, agent_lookup):
        """
        Processes interaction pairs [(agent_a_id, agent_b_id, distance), ...]
        and checks transmission between Infectious (I) and Susceptible (S).
        Returns a tuple: (newly_exposed_ids, interaction_records)
        """
        newly_exposed_ids = []
        interaction_records = []

        for item in interactions:
            if len(item) == 3:
                id_a, id_b, dist = item
            else:
                id_a, id_b = item[:2]
                dist = 1.5

            agent_a = agent_lookup.get(id_a)
            agent_b = agent_lookup.get(id_b)

            if not agent_a or not agent_b:
                continue

            transmission_attempted = False
            passed_on = False
            prob = 0.0
            prevention_reason = "No Active Infection Pair"
            infected_agent = None
            susceptible_agent = None

            # Check for Infectious <--> Susceptible pairing
            if agent_a["health_state"] == "I" and agent_b["health_state"] == "S":
                transmission_attempted = True
                infected_agent = agent_a
                susceptible_agent = agent_b
                passed_on, prob, prevention_reason = self._evaluate_pair_transmission(infected=agent_a, susceptible=agent_b, dist=dist)
                if passed_on:
                    newly_exposed_ids.append(agent_b["id"])

            elif agent_b["health_state"] == "I" and agent_a["health_state"] == "S":
                transmission_attempted = True
                infected_agent = agent_b
                susceptible_agent = agent_a
                passed_on, prob, prevention_reason = self._evaluate_pair_transmission(infected=agent_b, susceptible=agent_a, dist=dist)
                if passed_on:
                    newly_exposed_ids.append(agent_a["id"])
            else:
                # Interaction occurred between non-transmitting pairs (e.g. S-S, I-I, R-S)
                transmission_attempted = False
                passed_on = False
                prob = 0.0
                prevention_reason = f"No Transmission: Pairing ({agent_a['health_state']} <-> {agent_b['health_state']})"

            # Build rich interaction record for Lovable visualization
            record = {
                "agent_a": {
                    "id": agent_a["id"],
                    "health_state": agent_a.get("health_state", "S"),
                    "wearing_mask": agent_a.get("wearing_mask", False),
                    "social_distancing": agent_a.get("social_distancing", False) or agent_a.get("stay_home", False),
                    "hospitalized": agent_a.get("hospitalized", False),
                    "position": {"x": agent_a.get("x", 0.0), "y": agent_a.get("y", 0.0), "z": agent_a.get("z", 0.0)},
                    "personality": agent_a.get("personality", ""),
                    "occupation": agent_a.get("occupation", ""),
                    "age": agent_a.get("age", 30)
                },
                "agent_b": {
                    "id": agent_b["id"],
                    "health_state": agent_b.get("health_state", "S"),
                    "wearing_mask": agent_b.get("wearing_mask", False),
                    "social_distancing": agent_b.get("social_distancing", False) or agent_b.get("stay_home", False),
                    "hospitalized": agent_b.get("hospitalized", False),
                    "position": {"x": agent_b.get("x", 0.0), "y": agent_b.get("y", 0.0), "z": agent_b.get("z", 0.0)},
                    "personality": agent_b.get("personality", ""),
                    "occupation": agent_b.get("occupation", ""),
                    "age": agent_b.get("age", 30)
                },
                "location": agent_a.get("current_location", "city"),
                "distance": dist,
                "transmission_attempted": transmission_attempted,
                "passed_on": passed_on,
                "transmission_probability": round(prob, 4),
                "source_mask_active": infected_agent.get("wearing_mask", False) if infected_agent else False,
                "target_mask_active": susceptible_agent.get("wearing_mask", False) if susceptible_agent else False,
                "social_distancing_active": (infected_agent.get("social_distancing", False) or susceptible_agent.get("social_distancing", False)) if infected_agent and susceptible_agent else False,
                "prevention_reason": prevention_reason
            }
            interaction_records.append(record)

        return newly_exposed_ids, interaction_records

    def _evaluate_pair_transmission(self, infected, susceptible, dist=1.5):
        """
        Calculates exact pairwise transmission probability based on viral traits,
        mask usage, social distancing, physical distance, and immunity protection.
        """
        prob = self.base_transmission

        # Distance Factor (Greater distance reduces transmission)
        if dist > 2.0:
            prob *= max(0.2, 2.0 / dist)

        # Source Control (Infected person wearing a mask)
        source_masked = infected.get("wearing_mask", False)
        if source_masked:
            prob *= 0.30  # 70% reduction

        # Personal Protection (Susceptible person wearing a mask)
        target_masked = susceptible.get("wearing_mask", False)
        if target_masked:
            prob *= 0.70  # 30% reduction

        # Social Distancing modifier
        distancing_active = infected.get("social_distancing", False) or susceptible.get("social_distancing", False) or susceptible.get("stay_home", False)
        if distancing_active:
            prob *= 0.40  # 60% reduction

        # Immunity Protection & Escape
        immunity_factor = 1.0
        if susceptible.get("vaccinated", False):
            immunity_factor *= 0.40  # 60% reduction from vaccine
        if susceptible.get("previously_infected", False):
            immunity_factor *= 0.50  # 50% reduction from natural immunity

        effective_immunity = immunity_factor + (self.immune_escape * (1.0 - immunity_factor))
        prob *= effective_immunity

        final_prob = max(0.01, min(0.95, prob))

        # Roll for infection
        passed_on = random.random() <= final_prob
        if passed_on:
            susceptible["health_state"] = "E"
            susceptible["days_exposed"] = 0
            reason = "Infection Passed On (Transmission Successful)"
        else:
            if source_masked and target_masked:
                reason = "Prevented by Dual Mask Compliance"
            elif source_masked:
                reason = "Prevented by Source Mask Control"
            elif target_masked:
                reason = "Prevented by Personal Mask Protection"
            elif distancing_active:
                reason = "Prevented by Social Distancing"
            elif susceptible.get("vaccinated", False) or susceptible.get("previously_infected", False):
                reason = "Prevented by Immune Protection"
            elif dist > 2.0:
                reason = "Prevented by Physical Separation (>2m)"
            else:
                reason = "Prevented by Chance / Low Exposure"

        return passed_on, final_prob, reason

    # ============================================================
    # 2. DAILY DISEASE PROGRESSION (E -> I -> R / D & HOSPITALIZATION)
    # ============================================================

    def update_agent_health_states(self, agents):
        """
        Advances internal infection timers for all agents.
        Handles state transitions: S -> E -> I -> R / D, and Hospitalization.
        """
        new_infections = 0
        new_recoveries = 0
        new_deaths = 0

        for agent in agents:
            state = agent.get("health_state", "S")

            # --- EXPOSED -> INFECTED (Incubation Phase) ---
            if state == "E":
                agent["days_exposed"] = agent.get("days_exposed", 0) + 1
                if agent["days_exposed"] >= self.incubation_period:
                    agent["health_state"] = "I"
                    agent["days_infected"] = 0
                    new_infections += 1
                    
                    # Evaluate Hospitalization (Elderly or High-Risk get Hospitalized)
                    age = agent.get("age", 30)
                    hospital_prob = 0.60 if age >= 65 else (0.25 if age >= 50 else 0.10)
                    if random.random() <= hospital_prob:
                        agent["hospitalized"] = True
                        agent["current_location"] = agent.get("hospital_id", "hospital_1")
                    else:
                        agent["hospitalized"] = False

            # --- INFECTED -> RECOVERED / DECEASED (Infectious Phase) ---
            elif state == "I":
                agent["days_infected"] = agent.get("days_infected", 0) + 1
                
                # Keep hospitalized agents at hospital node
                if agent.get("hospitalized", False):
                    agent["current_location"] = agent.get("hospital_id", "hospital_1")

                if agent["days_infected"] >= self.recovery_period:
                    age = agent.get("age", 30)
                    adjusted_mortality = self.mortality_rate
                    
                    if age >= 65:
                        adjusted_mortality *= 3.0
                    elif age >= 50:
                        adjusted_mortality *= 1.5

                    if random.random() <= min(0.90, adjusted_mortality):
                        agent["health_state"] = "D"
                        agent["is_alive"] = False
                        agent["hospitalized"] = False
                        new_deaths += 1
                    else:
                        agent["health_state"] = "R"
                        agent["previously_infected"] = True
                        agent["hospitalized"] = False
                        new_recoveries += 1

            elif state in ["S", "R", "D"]:
                agent["hospitalized"] = False

        return {
            "new_infections": new_infections,
            "new_recoveries": new_recoveries,
            "new_deaths": new_deaths
        }

    # ============================================================
    # 3. VIRAL MUTATION ENGINE
    # ============================================================

    def check_for_mutation(self, total_active_infections):
        """
        Simulates viral mutation chance based on population infection load.
        """
        mutation_threshold = self.mutation_rate * (total_active_infections / 100.0)
        if random.random() <= min(0.50, mutation_threshold):
            self.base_transmission = min(0.95, self.base_transmission * 1.05)
            self.immune_escape = min(0.80, self.immune_escape * 1.03)
            return True, f"Variant mutated! Transmission increased to {round(self.base_transmission * 100, 1)}%"
        
        return False, ""