from controller.traci_manager import start_simulation, simulation_step, close_simulation
from controller.block_controller import BlockController
from controller.junction_controller import JunctionController
from controller.train_controller import TrainController
from controller.block_signal_controller import BlockSignalController

CONFIG = "config/rail.sumocfg"

def run():
    start_simulation(CONFIG)

    block_controller = BlockController()
    junction_controller = JunctionController(block_controller)
    block_signal_controller = BlockSignalController(block_controller, junction_controller)
    train_controller = TrainController(block_controller, junction_controller)

    step = 0
    while step < 350:
        simulation_step()

        block_controller.update_occupancy()
        train_controller.update_trains()
        block_signal_controller.update()

        block_controller.print_status()

        step += 1

    close_simulation()

if __name__ == "__main__":
    run()