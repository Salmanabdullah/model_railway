import traci
import sumolib

SUMO_CMD = "sumo-gui"

def start_simulation(config_path):
    traci.start([SUMO_CMD, "-c", config_path])

def simulation_step():
    traci.simulationStep()

def close_simulation():
    traci.close()