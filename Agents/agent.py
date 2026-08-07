# ================================================================
# Agents/agent.py
#
# Agent data class representing an individual in the simulation.
# ================================================================

class Agent:
    def __init__(self, agent_id: int, personality: str, age: int = 30, occupation: str = "Office Worker"):
        self.id = agent_id
        self.personality = personality
        self.age = age
        self.occupation = occupation
        
        # Epidemiology states: S (Susceptible), E (Exposed), I (Infected), R (Recovered), D (Deceased)
        self.health_state = "S"
        self.days_exposed = 0
        self.days_infected = 0
        self.is_alive = True
        
        # Protection & Immune traits
        self.wearing_mask = False
        self.vaccinated = False
        self.previously_infected = False
        self.has_comorbidities = False
        self.mask_probability = 0.5
        self.mask_days_worn = 0
        
        # Decision & Behavior states
        self.risk_score = 0.0
        self.stay_home = False
        self.go_outside = True
        self.remote_work = False
        self.attend_school = False
        self.visit_market = False
        self.travel = False
        self.seek_vaccination = False
        
        # Spatial locations
        self.home_id = ""
        self.primary_day_location = ""
        self.secondary_location = ""
        self.current_location = ""

    def to_dict(self) -> dict:
        return self.__dict__