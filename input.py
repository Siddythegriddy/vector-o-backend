# ================================================================
# input.py
#
# Configurator for Epidemic Simulator
# Prompts user for simulation settings, settlement types, 
# virus parameters, personality distribution, and policies,
# then saves to data/config.json AND automatically executes simulation.py
# ================================================================

import os
import sys
import json
import subprocess


def get_user_inputs():
    print("=========================================================")
    print("      EPIDEMIC SIMULATION ENGINE - INPUT CONFIGURATION   ")
    print("=========================================================\n")

    # 1. SETTLEMENT TYPE SELECTION
    print("Select Settlement Type:")
    print("  [1] Suburban (Medium density, balanced)")
    print("  [2] Metropolis (High density, subway/offices)")
    print("  [3] Rural Village (Low density, spread out)")
    print("  [4] Enclosed Facility (High contact, dorms/cafeterias)")
    
    settlement_choice = input("Enter choice [1-4, default 1]: ").strip()
    settlement_map = {
        "1": "Suburban",
        "2": "Metropolis",
        "3": "Rural Village",
        "4": "Enclosed Facility"
    }
    selected_settlement = settlement_map.get(settlement_choice, "Suburban")
    print(f"-> Selected Settlement: {selected_settlement}\n")

    # 2. VIRUS CHARACTERISTICS
    print("Virus Parameters:")
    try:
        transmission_rate = float(input(" - Base Transmission Rate % [default 35.0]: ") or "35.0")
        mortality_rate = float(input(" - Mortality Rate % [default 2.0]: ") or "2.0")
        incubation_days = int(input(" - Incubation Period (Days) [default 5]: ") or "5")
        recovery_days = int(input(" - Recovery Period (Days) [default 14]: ") or "14")
    except ValueError:
        print("Invalid virus parameters entered! Using defaults (35% Transmission, 2% Mortality, 5d Incubation, 14d Recovery).")
        transmission_rate, mortality_rate, incubation_days, recovery_days = 35.0, 2.0, 5, 14

    # 3. GENERAL SIMULATION PARAMETERS
    print("\nGeneral Settings:")
    try:
        days = int(input(" - Enter number of simulation days [default 10]: ") or "10")
        initial_infections = int(input(" - Enter initial infected agents [default 2]: ") or "2")
    except ValueError:
        print("Invalid number entered! Using defaults (10 days, 2 initial infected).")
        days = 10
        initial_infections = 2

    # 4. EXPANDED PERSONALITY POPULATION SIZES
    print("\nPopulation Sizes for Personalities:")
    try:
        extrovert_pop = int(input(" - Extroverts count [default 20]: ") or "20")
        introvert_pop = int(input(" - Introverts count [default 15]: ") or "15")
        senior_pop = int(input(" - Cautious Seniors count [default 10]: ") or "10")
        worker_pop = int(input(" - Essential Workers count [default 15]: ") or "15")
        children_pop = int(input(" - Children count [default 15]: ") or "15")
        traveler_pop = int(input(" - Travelers count [default 5]: ") or "5")
    except ValueError:
        print("Invalid population numbers entered! Using defaults.")
        extrovert_pop, introvert_pop, senior_pop, worker_pop, children_pop, traveler_pop = 20, 15, 10, 15, 15, 5

    # 5. GOVERNMENT POLICIES
    print("\nToggle Government Policies (y/n):")
    mask_rule = input(" - Enable Mask Mandate? [y/N]: ").strip().lower() == 'y'
    lockdown = input(" - Enable Lockdown? [y/N]: ").strip().lower() == 'y'
    curfew = input(" - Enable Night Curfew? [y/N]: ").strip().lower() == 'y'

    # BUILD CONFIGURATION DICTIONARY WITH PROBABILISTIC MASK COMPLIANCE
    config = {
        "days": days,
        "initial_infections": initial_infections,
        "virus": {
            "transmission": transmission_rate,
            "mortality": mortality_rate,
            "incubation": incubation_days,
            "recovery": recovery_days
        },
        "settlement": {
            "type": selected_settlement
        },
        "personalities": [
            {"Name": "Extrovert", "Population": extrovert_pop, "Social": 8, "Mobility": 8, "MaskProbability": 0.50},
            {"Name": "Introvert", "Population": introvert_pop, "Social": 2, "Mobility": 3, "MaskProbability": 0.85},
            {"Name": "Cautious Senior", "Population": senior_pop, "Social": 3, "Mobility": 2, "MaskProbability": 0.90},
            {"Name": "Essential Worker", "Population": worker_pop, "Social": 6, "Mobility": 7, "MaskProbability": 0.65},
            {"Name": "Children", "Population": children_pop, "Social": 7, "Mobility": 5, "MaskProbability": 0.20},
            {"Name": "Travelers", "Population": traveler_pop, "Social": 9, "Mobility": 10, "MaskProbability": 0.25}
        ],
        "policies": {
            "mask_rule": mask_rule,
            "lockdown": lockdown,
            "curfew": curfew
        }
    }

    # 6. CONFIRMATION SUMMARY
    total_population = sum([extrovert_pop, introvert_pop, senior_pop, worker_pop, children_pop, traveler_pop])
    print("\n" + "=" * 55)
    print("                    CONFIG SUMMARY                  ")
    print("=" * 55)
    print(f" Settlement:    {selected_settlement}")
    print(f" Duration:      {days} Days | Initial Infections: {initial_infections}")
    print(f" Virus Profile: {transmission_rate}% Transmission, {mortality_rate}% Mortality")
    print(f" Total Agents:  {total_population}")
    print(f" Policies:      Masks={mask_rule}, Lockdown={lockdown}, Curfew={curfew}")
    print("=" * 55)

    confirm = input("\nStart simulation with these settings? [Y/n]: ").strip().lower()
    if confirm not in ['y', 'yes', '']:
        print("Simulation launch cancelled. Configuration was not executed.")
        return None

    # 7. SAVE TO data/config.json
    root_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    config_path = os.path.join(data_dir, "config.json")

    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)

    print(f"\n[+] Configuration saved to: {config_path}")
    print("[+] Launching simulation engine...\n")

    # 8. AUTOMATICALLY RUN simulation.py
    sim_path = os.path.join(root_dir, "Simulation", "simulation.py")
    subprocess.run([sys.executable, sim_path])

    return config


if __name__ == "__main__":
    get_user_inputs()