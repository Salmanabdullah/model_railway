import traci
from utils.constants import BLOCKS

class BlockController:

    def __init__(self):
        self.block_occupancy = {block: None for block in BLOCKS}

    def update_occupancy(self):
        # Reset all
        for block in self.block_occupancy:
            self.block_occupancy[block] = None

        # Check each block
        for block, edges in BLOCKS.items():
            for edge in edges:
                vehicles = traci.edge.getLastStepVehicleIDs(edge)
                if vehicles:
                    self.block_occupancy[block] = vehicles[0]
                    break

    def is_block_free(self, block):
        return self.block_occupancy.get(block) is None

    def get_train_block(self, train_id):
        edge = traci.vehicle.getRoadID(train_id)
        from utils.constants import EDGE_TO_BLOCK
        return EDGE_TO_BLOCK.get(edge)

    def print_status(self):
        print("\nBlock Status:")
        for b, v in self.block_occupancy.items():
            print(f"{b}: {'FREE' if v is None else v}")