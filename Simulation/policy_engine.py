# ================================================================
# policy_engine.py
#
# Phase 9: Government Policy Engine
#
# Manages active public health interventions and applies policy 
# overrides directly to population risk, agent decision rules, 
# and routine dynamics.
#
# Policies Supported:
#   1. Lockdown (Forces stay_home, reduces mobility)
#   2. School Closure (Closes schools, forces remote learning)
#   3. Mask Rule (Mandates mask usage across population)
#   4. Vaccination Campaign (Accelerates vaccine uptake)
#   5. Testing & Contact Tracing (Detects and isolates infected)
#   6. Travel Restriction (Blocks inter-zone movement)
#   7. Curfew (Restricts evening/night movement hours)
#   8. Awareness Campaign (Elevates baseline population risk score)
# ================================================================

import random


class PolicyEngine:
    def __init__(self):
        """
        Initializes policy toggles and parameters.
        Default state: All interventions inactive.
        """
        self.active_policies = {
            "lockdown": False,
            "school_closure": False,
            "mask_rule": False,
            "vaccination_campaign": False,
            "testing_and_tracing": False,
            "travel_restriction": False,
            "curfew": False,
            "awareness_campaign": False,
        }

        # Policy configuration thresholds/intensities
        self.curfew_start_hour = 20  # 8:00 PM curfew by default
        self.daily_testing_capacity = 0.10  # Tests 10% of population daily
        self.awareness_risk_boost = 15.0  # Boosts risk perception by +15 points

    def update_policies(self, policy_config):
        """
        Updates active policy states from API inputs or automated triggers.
        e.g., policy_config = {"lockdown": True, "mask_rule": True}
        """
        for policy, state in policy_config.items():
            if policy in self.active_policies:
                self.active_policies[policy] = bool(state)

    # ============================================================
    # 1. APPLY POLICIES TO RISK & DECISIONS (MORNING)
    # ============================================================

    def apply_morning_policies(self, agents, risk_engine):
        """
        Applies policy effects on agent risk perception and daily decisions.
        Runs every morning right after Phase 7 Risk Engine calculations.
        """
        for agent in agents:
            # --- Policy 8: Awareness Campaign ---
            # Increases baseline risk perception across the entire population
            if self.active_policies["awareness_campaign"]:
                agent["risk_score"] = min(100.0, agent.get("risk_score", 0.0) + self.awareness_risk_boost)

            # --- Policy 3: Mask Mandate ---
            # Forces compliance unless the agent is a strict skeptic
            if self.active_policies["mask_rule"]:
                if agent.get("personality") != "Skeptic":
                    agent["wearing_mask"] = True

            # --- Policy 1: Lockdown ---
            # Forces agents to stay home except for Essential Workers
            if self.active_policies["lockdown"]:
                if agent.get("occupation") not in ["Essential Worker", "Healthcare Worker"]:
                    agent["stay_home"] = True
                    agent["go_outside"] = False
                    agent["remote_work"] = True
                    agent["visit_market"] = False
                    agent["travel"] = False

            # --- Policy 2: School Closure ---
            if self.active_policies["school_closure"]:
                if agent.get("occupation") == "Student" or agent.get("age", 30) < 18:
                    agent["attend_school"] = False

            # --- Policy 6: Travel Restriction ---
            if self.active_policies["travel_restriction"]:
                agent["travel"] = False

            # --- Policy 4: Vaccination Campaign ---
            # Boosts willingness to get vaccinated regardless of risk score
            if self.active_policies["vaccination_campaign"] and not agent.get("vaccinated", False):
                if random.random() <= 0.25:  # 25% daily vaccination rate during active push
                    agent["seek_vaccination"] = True
                    agent["vaccinated"] = True

        # --- Policy 5: Testing & Contact Tracing ---
        # Detects infected agents (including asymptomatic) and forces strict isolation
        if self.active_policies["testing_and_tracing"]:
            self._run_testing_and_tracing(agents)

        return agents

    def _run_testing_and_tracing(self, agents):
        """
        Randomly tests a sample of the population and isolates positive cases.
        """
        sample_size = int(len(agents) * self.daily_testing_capacity)
        tested_agents = random.sample(agents, min(sample_size, len(agents)))

        for agent in tested_agents:
            if agent.get("health_state") in ["E", "I"]:
                agent["is_tested_positive"] = True
                agent["stay_home"] = True  # Strict quarantine
                agent["go_outside"] = False

    # ============================================================
    # 2. APPLY POLICIES TO ROUTINES & HOURLY MOVEMENT (HOURLY)
    # ============================================================

    def enforce_hourly_curfew(self, agent, current_hour):
        """
        Policy 7: Curfew Enforcement.
        Forces agents back home during curfew hours regardless of plans.
        """
        if self.active_policies["curfew"] and current_hour >= self.curfew_start_hour:
            if agent.get("occupation") not in ["Healthcare Worker", "Essential Worker"]:
                agent["current_location"] = agent.get("home_id", "home_default")