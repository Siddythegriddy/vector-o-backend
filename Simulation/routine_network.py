# ================================================================
# routine_network.py
#
# Phase 4 & 5: Social Network Engine & Daily Routine Generator
#
# Phase 4: NetworkX Graph / Social Edge Creation (Family, Work, Friends)
# Phase 5: 24-Hour Time-Step Routine Execution Loop
# ================================================================

import random
from typing import List, Dict, Any


# ================================================================
# PHASE 4: SOCIAL NETWORK ENGINE
# ================================================================

class SocialNetworkEngine:
    """
    Generates structured social relationship networks across the agent population.
    Creates family, coworker/schoolmate, and friendship connections.
    """

    def __init__(self, agents: List[Dict[str, Any]], nodes: Dict[str, Any]):
        self.agents = agents
        self.nodes = nodes
        # Adjacency list representation: { agent_id: { target_agent_id: relation_type } }
        self.graph: Dict[int, Dict[int, str]] = {a["id"]: {} for a in agents}

    def build_network(self):
        """Builds all social graph layers."""
        self._build_family_edges()
        self._build_workplace_edges()
        self._build_friendship_edges()
        return self.graph

    def _add_edge(self, id1: int, id2: int, relation_type: str):
        """Adds a bi-directional social edge between two agents."""
        if id1 != id2:
            self.graph[id1][id2] = relation_type
            self.graph[id2][id1] = relation_type

    def _build_family_edges(self):
        """Connects agents sharing the same home or dorm node."""
        home_buckets: Dict[str, List[int]] = {}
        for agent in self.agents:
            home_id = agent.get("home_id", "default_home")
            home_buckets.setdefault(home_id, []).append(agent["id"])

        for members in home_buckets.values():
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    self._add_edge(members[i], members[j], "family")

    def _build_workplace_edges(self):
        """Connects agents sharing the same workplace or school primary node."""
        work_buckets: Dict[str, List[int]] = {}
        for agent in self.agents:
            primary_loc = agent.get("primary_day_location")
            if primary_loc and "home" not in primary_loc:
                work_buckets.setdefault(primary_loc, []).append(agent["id"])

        for colleagues in work_buckets.values():
            # Connect cluster members with high probability
            for i in range(len(colleagues)):
                # Pick up to 5 close workplace peers
                sample_size = min(5, len(colleagues))
                peers = random.sample(colleagues, sample_size)
                for peer in peers:
                    self._add_edge(colleagues[i], peer, "coworker")

    def _build_friendship_edges(self):
        """Generates random friendship edges based on social activity score."""
        for agent in self.agents:
            # Chance to form external friend edges
            social_score = agent.get("social_activity", 5)
            num_friends = random.randint(1, max(1, int(social_score / 2)))

            possible_friends = random.sample(self.agents, min(num_friends * 2, len(self.agents)))
            for friend in possible_friends:
                if friend["id"] != agent["id"] and friend["id"] not in self.graph[agent["id"]]:
                    self._add_edge(agent["id"], friend["id"], "friend")


# ================================================================
# PHASE 5: DAILY ROUTINE GENERATOR (24-HOUR CLOCK)
# ================================================================

class DailyRoutineGenerator:
    """
    Simulates a 24-hour daily cycle and manages agent spatial mobility.
    Updates agent positions based on time of day and isolation state.
    """

    def __init__(self, agents: List[Dict[str, Any]]):
        self.agents = agents

    def update_agent_positions(self, hour: int) -> List[Dict[str, Any]]:
        """
        Updates each agent's `current_location` depending on the hour (0 - 23).
        
        Routine Schedule Breakdown:
          • 00:00 - 07:00 -> At Home (Sleeping/Resting)
          • 08:00 - 16:00 -> At Work / School (Primary Location)
          • 17:00 - 20:00 -> At Public/Social Space (Secondary Location)
          • 21:00 - 23:00 -> Returning Home
        """
        for agent in self.agents:
            # If agent is isolating/staying home, ignore routine and stay home
            if agent.get("stay_home", False):
                agent["current_location"] = agent.get("home_id", "default_home")
                continue

            # --- MORNING (HOME) ---
            if 0 <= hour < 8:
                agent["current_location"] = agent.get("home_id", "default_home")

            # --- DAYTIME (WORK / SCHOOL) ---
            elif 8 <= hour < 17:
                # Extroverts/Essential workers are guaranteed to go; introverts might skip on weekends/high risk
                agent["current_location"] = agent.get("primary_day_location", agent.get("home_id"))

            # --- EVENING (SOCIAL / MARKET / PARK) ---
            elif 17 <= hour < 21:
                # Mobility check: higher mobility means higher chance to go out in evening
                mobility = agent.get("movement_today", 5)
                if random.random() * 10 <= mobility:
                    agent["current_location"] = agent.get("secondary_location", agent.get("home_id"))
                else:
                    agent["current_location"] = agent.get("home_id", "default_home")

            # --- NIGHT (HOME) ---
            else:
                agent["current_location"] = agent.get("home_id", "default_home")

        return self.agents