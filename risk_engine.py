# ================================================================
# risk_engine.py
#
# Phase 7: Dynamic Environmental & Individual Risk Engine
#
# Calculates daily risk score (0 - 100) for every agent based on:
#   - Global Environmental Inputs: Hospital Load, Government Alerts, Settlement Type
#   - Local Community Dynamics: Nearby Active Cases
#   - Individual Biological Factors: Age, Health Conditions, Vaccination, Immunity
#   - Social & Personality Characteristics: Occupation & Risk Sensitivity
# ================================================================


class RiskEngine:
    def __init__(self, settlement_type="Suburban", alert_level="None"):
        """
        Initializes global environment parameters that affect all agents.
        """
        self.settlement_type = settlement_type
        self.alert_level = alert_level  # "None", "Yellow", "Orange", "Red"

        # Settlement density risk multiplier
        self.settlement_risk_weights = {
            "Metropolis": 20.0,
            "Enclosed Facility": 25.0,
            "Suburban": 10.0,
            "Rural Village": 5.0,
        }

        # Government alert level risk weights
        self.alert_weights = {
            "None": 0.0,
            "Yellow": 10.0,
            "Orange": 20.0,
            "Red": 35.0,
        }

    # ============================================================
    # CALCULATE DAILY RISK SCORE FOR ALL AGENTS
    # ============================================================

    def evaluate_daily_population_risk(
        self, agents, active_cases, total_population, hospital_capacity=100
    ):
        """
        Calculates daily risk score for every agent in the population.
        
        Parameters
        ----------
        agents : list of dicts
        active_cases : int (total currently infected agents)
        total_population : int
        hospital_capacity : int (max hospital bed capacity)
        """
        # 1. GLOBAL CALCULATIONS
        # Infection Rate in Community (%)
        infection_rate = (
            (active_cases / total_population) * 100.0 if total_population > 0 else 0.0
        )

        # Hospital Load Impact (0 to 25 points)
        hospital_load_ratio = active_cases / max(1, hospital_capacity)
        hospital_risk_score = min(25.0, hospital_load_ratio * 15.0)

        # Settlement baseline risk
        base_settlement_risk = self.settlement_risk_weights.get(
            self.settlement_type, 10.0
        )

        # Government Alert risk
        gov_alert_risk = self.alert_weights.get(self.alert_level, 0.0)

        # 2. INDIVIDUAL AGENT EVALUATION LOOP
        for agent in agents:
            risk = 0.0

            # --- A. Nearby / Community Cases Factor ---
            risk += min(30.0, infection_rate * 1.5)

            # --- B. Settlement & Environmental Risk ---
            risk += base_settlement_risk
            risk += gov_alert_risk
            risk += hospital_risk_score

            # --- C. Occupation Risk ---
            occupation = agent.get("occupation", "Other")
            if occupation == "Healthcare Worker":
                risk += 25.0
            elif occupation in ["Essential Worker", "Teacher", "Retail"]:
                risk += 15.0
            elif occupation == "Office Worker":
                risk += 5.0

            # --- D. Age Vulnerability Factor ---
            age = agent.get("age", 30)
            if isinstance(age, str):
                age = 65 if "Senior" in age else (15 if "Student" in age else 35)

            if age >= 65:
                risk += 20.0
            elif age >= 50:
                risk += 12.0
            elif age >= 30:
                risk += 5.0

            # --- E. Pre-existing Health Conditions ---
            if agent.get("has_comorbidities", False):
                risk += 15.0

            # --- F. Vaccination Protection ---
            if agent.get("vaccinated", False):
                risk -= 18.0

            # --- G. Previous Infection (Natural Immunity) ---
            if agent.get("previously_infected", False):
                risk -= 10.0

            # --- H. Personality & Masking Modifiers ---
            personality = agent.get("personality", "Default")
            if personality == "Cautious Senior" or personality == "Anxious":
                risk += 10.0
            elif personality == "Skeptic" or personality == "Rebel":
                risk -= 15.0  # Skeptics perceive lower risk regardless of environment

            if agent.get("wearing_mask", False):
                risk -= 8.0

            # --- I. Final Clamp (0 to 100) ---
            final_risk = round(max(0.0, min(100.0, risk)), 2)
            agent["risk_score"] = final_risk

        return agents