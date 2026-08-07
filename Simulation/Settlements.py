# ================================================================
# settlement.py
#
# Settlement & Infrastructure Generator Module
#
# Generates spatial nodes (schools, workplaces, markets, homes)
# and assigns characteristics based on user-selected settlement type.
# ================================================================

import random

# Preset characteristics for each settlement archetype
SETTLEMENT_PROFILES = {
    "Metropolis": {
        "density_multiplier": 1.5,
        "location_types": ["office", "subway", "mall", "school", "hospital", "home"],
        "avg_node_capacity": 50,
        "base_contact_modifier": 1.3,
        "description": "High-density urban center with public transit and large workplace clusters."
    },
    "Suburban": {
        "density_multiplier": 1.0,
        "location_types": ["office", "local_market", "school", "hospital", "park", "home"],
        "avg_node_capacity": 25,
        "base_contact_modifier": 1.0,
        "description": "Medium-density residential area with balanced community and work nodes."
    },
    "Rural Village": {
        "density_multiplier": 0.6,
        "location_types": ["community_center", "local_market", "school", "hospital", "home"],
        "avg_node_capacity": 12,
        "base_contact_modifier": 0.7,
        "description": "Low-density spread-out community with strong local gathering points."
    },
    "Enclosed Facility": {
        "density_multiplier": 2.0,
        "location_types": ["cafeteria", "common_room", "work_unit", "infirmary_hospital", "dorm"],
        "avg_node_capacity": 40,
        "base_contact_modifier": 1.6,
        "description": "High-contact confined environment such as a campus, factory, or care home."
    }
}


# Alias map for case normalization
SETTLEMENT_ALIASES = {
    "metropolis": "Metropolis",
    "metropolitan": "Metropolis",
    "suburban": "Suburban",
    "rural village": "Rural Village",
    "rural": "Rural Village",
    "enclosed facility": "Enclosed Facility",
    "enclosed": "Enclosed Facility"
}

class SettlementGenerator:
    def __init__(self, settlement_type="Suburban", custom_config=None):
        """
        Initializes settlement rules with case-insensitive archetype matching.
        """
        raw_type = str(settlement_type).strip().lower()
        normalized_type = SETTLEMENT_ALIASES.get(raw_type, "Suburban")

        self.settlement_type = normalized_type
        self.profile = SETTLEMENT_PROFILES[normalized_type].copy()

        # Allow user/API overrides
        if custom_config:
            self.profile.update(custom_config)

    def generate_settlement_nodes(self, total_population):
        """
        Generates spatial locations (nodes) with 2D/3D city coordinates based on population and settlement archetype.
        Returns a dictionary of location nodes.
        """
        capacity = self.profile["avg_node_capacity"]
        num_nodes_per_type = max(1, int(total_population / capacity))

        nodes = {}
        node_id_counter = 1

        # Zonal bounds for 3D City Layout (100x100 grid)
        zones = {
            "home": {"x_min": 5, "x_max": 45, "y_min": 5, "y_max": 45, "height_3d": 12, "color": "#3B82F6"},
            "dorm": {"x_min": 5, "x_max": 45, "y_min": 5, "y_max": 45, "height_3d": 16, "color": "#3B82F6"},
            "office": {"x_min": 55, "x_max": 95, "y_min": 5, "y_max": 45, "height_3d": 35, "color": "#8B5CF6"},
            "work_unit": {"x_min": 55, "x_max": 95, "y_min": 5, "y_max": 45, "height_3d": 25, "color": "#8B5CF6"},
            "subway": {"x_min": 45, "x_max": 55, "y_min": 5, "y_max": 95, "height_3d": 5, "color": "#6B7280"},
            "school": {"x_min": 30, "x_max": 50, "y_min": 50, "y_max": 70, "height_3d": 18, "color": "#F59E0B"},
            "local_market": {"x_min": 55, "x_max": 75, "y_min": 50, "y_max": 70, "height_3d": 14, "color": "#10B981"},
            "mall": {"x_min": 55, "x_max": 95, "y_min": 50, "y_max": 70, "height_3d": 22, "color": "#10B981"},
            "community_center": {"x_min": 30, "x_max": 60, "y_min": 50, "y_max": 70, "height_3d": 15, "color": "#10B981"},
            "cafeteria": {"x_min": 40, "x_max": 60, "y_min": 40, "y_max": 60, "height_3d": 12, "color": "#10B981"},
            "common_room": {"x_min": 20, "x_max": 40, "y_min": 40, "y_max": 60, "height_3d": 10, "color": "#10B981"},
            "hospital": {"x_min": 10, "x_max": 35, "y_min": 75, "y_max": 95, "height_3d": 28, "color": "#EF4444"},
            "infirmary_hospital": {"x_min": 10, "x_max": 35, "y_min": 75, "y_max": 95, "height_3d": 24, "color": "#EF4444"},
            "park": {"x_min": 70, "x_max": 95, "y_min": 75, "y_max": 95, "height_3d": 2, "color": "#22C55E"}
        }

        for loc_type in self.profile["location_types"]:
            if loc_type in ["home", "dorm"]:
                count = max(1, int(total_population / 4))
            elif "hospital" in loc_type:
                count = max(1, int(total_population / 25))
            else:
                count = num_nodes_per_type

            zone_info = zones.get(loc_type, {"x_min": 10, "x_max": 90, "y_min": 10, "y_max": 90, "height_3d": 15, "color": "#6366F1"})

            for _ in range(count):
                node_key = f"{loc_type}_{node_id_counter}"
                node_x = random.uniform(zone_info["x_min"], zone_info["x_max"])
                node_y = random.uniform(zone_info["y_min"], zone_info["y_max"])
                
                nodes[node_key] = {
                    "id": node_key,
                    "type": loc_type,
                    "capacity": capacity,
                    "contact_modifier": self.profile["base_contact_modifier"],
                    "position": {
                        "x": round(node_x, 2),
                        "y": round(node_y, 2),
                        "z": 0.0
                    },
                    "dimensions": {
                        "width": random.uniform(6, 12),
                        "length": random.uniform(6, 12),
                        "height": zone_info["height_3d"]
                    },
                    "color": zone_info["color"]
                }
                node_id_counter += 1

        return nodes

    def assign_agents_to_settlement(self, agents, nodes):
        """
        Distributes agents across homes, workplaces, schools, hospitals, and markets.
        Ensures agents have deterministic daily routines.
        """
        homes = [nid for nid, n in nodes.items() if "home" in n["type"] or "dorm" in n["type"]]
        workplaces = [nid for nid, n in nodes.items() if any(k in n["type"] for k in ["office", "subway", "cafeteria", "work_unit"])]
        public_spaces = [nid for nid, n in nodes.items() if any(k in n["type"] for k in ["market", "mall", "park", "community_center", "common_room"])]
        schools = [nid for nid, n in nodes.items() if "school" in n["type"]]
        hospitals = [nid for nid, n in nodes.items() if "hospital" in n["type"]]

        for idx, agent in enumerate(agents):
            # 1. Assign Home
            agent["home_id"] = homes[idx % len(homes)] if homes else "home_default"

            # 2. Assign Day Location based on age / personality
            age = agent.get("age", 30)
            if isinstance(age, str):
                age = 65 if "Senior" in age else (15 if "Student" in age else 35)

            if age < 18 and schools:
                agent["primary_day_location"] = schools[idx % len(schools)]
            elif workplaces:
                agent["primary_day_location"] = workplaces[idx % len(workplaces)]
            else:
                agent["primary_day_location"] = agent["home_id"]

            # 3. Assign Secondary/Social Location
            if public_spaces:
                agent["secondary_location"] = public_spaces[idx % len(public_spaces)]
            else:
                agent["secondary_location"] = agent["home_id"]

            # 4. Assign Hospital Node
            agent["hospital_id"] = hospitals[idx % len(hospitals)] if hospitals else "hospital_default"

            # Set starting location to home
            agent["current_location"] = agent["home_id"]

        return agents