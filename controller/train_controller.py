import traci

class TrainController:

    def __init__(self, block_controller, junction_controller):
        self.block_controller = block_controller
        self.junction_controller = junction_controller

    def update_trains(self):
        vehicles = traci.vehicle.getIDList()

        for v in vehicles:
            self.junction_controller.control_train(v)