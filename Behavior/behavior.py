# ================================================================
# behavior.py
#
# Phase 8: Advanced Behavioral Decision Engine
#
# Inputs:
#   - Risk Score (from Phase 7 Risk Engine)
#   - Personality Profiles
#   - Settlement Archetype
#
# Outputs Daily Decisions:
#   - go_outside / stay_home
#   - wear_mask
#   - visit_market
#   - attend_school
#   - remote_work
#   - travel
# ================================================================

import random

# Personality Cross-Affinity Matrix for interaction probabilities
PERSONALITY_AFFINITY_MATRIX = {
    "Extrovert": {"Extrovert": 1.4, "Introvert": 0.5, "Essential Worker": 1.2, "Skeptic": 1.3, "Cautious Senior": 0.3},
    "Introvert": {"Extrovert": 0.5, "Introvert": 0.8, "Essential Worker": 0.7, "Skeptic": 0.4, "Cautious Senior": 0.7},
    "Essential Worker": {"Extrovert": 1.2, "Introvert": 0.7, "Essential Worker": 1.3, "Skeptic": 1.1, "Cautious Senior": 1.0},
    "Skeptic": {"Extrovert": 1.3, "Introvert": 0.4, "Essential Worker": 1.1, "Skeptic": 1.5, "Cautious Senior": 0.2},
    "Cautious Senior": {"Extrovert": 0.3, "Introvert": 0.7, "Essential Worker": 1.0, "Skeptic": 0.2, "Cautious Senior": 1.3},
}


class BehaviorEngine:
    def __init__(self, virus_data, personalities, settlement_type="Suburban"):
        """
        Initializes the Phase 8 Behavior Engine with virus, personality profiles, and settlement context.
        """
        self.virus = virus_data
        self.settlement_type = settlement_type

        if isinstance(personalities, list):
            self.personalities = {p["Name"]: p for p in personalities if "Name" in p}
        else:
            self.personalities = personalities

    def get_personality(self, agent):
        """Safe lookup for personality profile."""
        p_name = agent.get("personality", "")
        if p_name in self.personalities:
            return self.personalities[p_name]

        return {
            "Name": p_name or "Default",
            "Social": agent.get("social_activity", 5),
            "Mobility": agent.get("mobility", 5),
            "Mask": agent.get("mask_usage", "Sometimes"),
            "Vaccine": agent.get("vaccination_behaviour", "Delayed"),
            "Isolation": agent.get("isolation_threshold", 50),
        }

    # ============================================================
    # PHASE 8: DAILY DECISION ENGINE
    # ============================================================

    def decide_behaviour(self, agent):
        """
        Evaluates Risk Score + Personality + Settlement to determine all Phase 8 decisions.
        """
        personality = self.get_personality(agent)
        risk = agent.get("risk_score", 0.0)

        # Retrieve profile thresholds
        isolation_thresh = float(personality.get("Isolation", personality.get("isolation_threshold", 50)))
        mask_pref = personality.get("Mask", personality.get("mask_usage", "Sometimes"))
        vaccine_pref = personality.get("Vaccine", personality.get("vaccination_behaviour", "Delayed"))
        occupation = agent.get("occupation", "Other")

        # --------------------------------------------------------
        # 1. STAY HOME / ISOLATION & SOCIAL DISTANCING DECISION
        # --------------------------------------------------------
        if risk >= isolation_thresh:
            agent["stay_home"] = True
            agent["go_outside"] = False
            agent["social_distancing"] = True
        else:
            agent["stay_home"] = False
            agent["go_outside"] = True
            # Social distancing active if risk is moderate or introvert/cautious personality
            p_name = personality.get("Name", "")
            agent["social_distancing"] = (risk >= 35.0) or (p_name in ["Introvert", "Cautious Senior"])

        # --------------------------------------------------------
        # 2. MASK DECISION
        # --------------------------------------------------------
        if mask_pref == "Always":
            agent["wearing_mask"] = True
        elif mask_pref == "Sometimes" and risk >= 35:
            agent["wearing_mask"] = True
        else:
            agent["wearing_mask"] = False

        # --------------------------------------------------------
        # 3. WORK & SCHOOL DECISIONS (Remote Work vs. Attend School)
        # --------------------------------------------------------
        age = agent.get("age", 30)
        if isinstance(age, str):
            age = 15 if "Student" in age else (65 if "Senior" in age else 35)

        # School Decision
        if age < 18 or occupation == "Student":
            # High risk or strict settlement causes school closures / remote learning
            if risk >= 60 or self.settlement_type == "Enclosed Facility" and risk >= 45:
                agent["attend_school"] = False
            else:
                agent["attend_school"] = not agent["stay_home"]
            agent["remote_work"] = False
        else:
            agent["attend_school"] = False

            # Remote Work Decision
            if occupation in ["Healthcare Worker", "Essential Worker", "Retail"]:
                agent["remote_work"] = False  # Essential roles cannot work remotely
            elif risk >= 50 or self.settlement_type == "Metropolis" and risk >= 40:
                agent["remote_work"] = True
            else:
                agent["remote_work"] = False

        # --------------------------------------------------------
        # 4. VISIT MARKET / SOCIAL DECISION
        # --------------------------------------------------------
        social_score = float(personality.get("Social", personality.get("social_activity", 5)))

        if agent["stay_home"]:
            agent["visit_market"] = False
        elif risk >= 70:
            agent["visit_market"] = False  # Market visits canceled during extreme risk
        else:
            # Chance to visit market depends on social activity and settlement
            visit_prob = (social_score / 10.0) * (1.0 - (risk / 100.0))
            if self.settlement_type == "Rural Village":
                visit_prob *= 1.2  # Higher dependency on local central market
            agent["visit_market"] = random.random() <= max(0.1, visit_prob)

        # --------------------------------------------------------
        # 5. TRAVEL DECISION
        # --------------------------------------------------------
        mobility_score = float(personality.get("Mobility", personality.get("mobility", 5)))

        if agent["stay_home"] or risk >= 55:
            agent["travel"] = False
        else:
            # Metropolis and Suburban areas see higher inter-zone travel
            travel_baseline = 0.15 if self.settlement_type in ["Metropolis", "Suburban"] else 0.05
            travel_prob = travel_baseline * (mobility_score / 5.0) * (1.0 - (risk / 100.0))
            agent["travel"] = random.random() <= max(0.0, travel_prob)

        # --------------------------------------------------------
        # 6. SEEK VACCINATION DECISION
        # --------------------------------------------------------
        if not agent.get("vaccinated", False):
            if vaccine_pref == "Immediate" and risk >= 15:
                agent["seek_vaccination"] = True
            elif vaccine_pref == "Delayed" and risk >= 50:
                agent["seek_vaccination"] = True
            else:
                agent["seek_vaccination"] = False

        return agent

    # ============================================================
    # SPATIAL GRID & PAIRWISE INTERACTION ENGINE
    # ============================================================

    def interaction_probability(self, agent_a, agent_b):
        """Calculates pairwise interaction chance based on decisions and affinities."""
        p_a = self.get_personality(agent_a)
        p_b = self.get_personality(agent_b)

        soc_a = float(p_a.get("Social", p_a.get("social_activity", 5)))
        soc_b = float(p_b.get("Social", p_b.get("social_activity", 5)))
        mob_a = float(p_a.get("Mobility", p_a.get("mobility", 5)))
        mob_b = float(p_b.get("Mobility", p_b.get("mobility", 5)))

        prob = (((soc_a + soc_b) / 20.0) * 0.60) + (((mob_a + mob_b) / 20.0) * 0.40)

        # Apply personality affinity matrix
        name_a = p_a.get("Name", "")
        name_b = p_b.get("Name", "")
        if name_a in PERSONALITY_AFFINITY_MATRIX and name_b in PERSONALITY_AFFINITY_MATRIX[name_a]:
            prob *= PERSONALITY_AFFINITY_MATRIX[name_a][name_b]

        # Phase 8 Decision impact modifiers
        if agent_a.get("stay_home", False) and agent_b.get("stay_home", False):
            prob *= 0.05
        elif agent_a.get("stay_home", False) or agent_b.get("stay_home", False):
            prob *= 0.20

        if agent_a.get("wearing_mask", False) and agent_b.get("wearing_mask", False):
            prob *= 0.85

        return max(0.0, min(0.95, round(prob, 4)))

    def simulate_grid_interactions(self, agents):
        """O(N) Spatial/Grid Interaction Engine with distance computation."""
        location_buckets = {}
        for agent in agents:
            loc_id = agent.get("current_location", "default_location")
            location_buckets.setdefault(loc_id, []).append(agent)

        all_interactions = []
        for loc_id, agents_in_loc in location_buckets.items():
            if len(agents_in_loc) < 2:
                continue

            n = len(agents_in_loc)
            for i in range(n):
                for j in range(i + 1, n):
                    a_a = agents_in_loc[i]
                    a_b = agents_in_loc[j]
                    if random.random() <= self.interaction_probability(a_a, a_b):
                        # Calculate distance between agents in meters / grid units
                        dx = a_a.get("x", 0.0) - a_b.get("x", 0.0)
                        dy = a_a.get("y", 0.0) - a_b.get("y", 0.0)
                        dz = a_a.get("z", 0.0) - a_b.get("z", 0.0)
                        dist = round((dx*dx + dy*dy + dz*dz)**0.5, 2)
                        # Default to reasonable distance if position not set
                        if dist == 0.0:
                            dist = round(random.uniform(0.5, 3.0), 2)
                        all_interactions.append((a_a["id"], a_b["id"], dist))

        return all_interactions