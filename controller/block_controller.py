import traci
from utils.constants import BLOCKS

class BlockController:

    def __init__(self):
        self.block_occupancy = {block: None for block in BLOCKS}
        self.previous_block_occupancy = self.block_occupancy.copy()

    def update_occupancy(self):
        # save previous snapshot
        self.previous_block_occupancy = self.block_occupancy.copy()

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

    # Print status of all blocks (for debugging)
    # def print_status(self):
    #     print("\nBlock Status:")
    #     for b, v in self.block_occupancy.items():
    #         print(f"{b}: {'FREE' if v is None else v}")

    # Improved print_status to only show occupied blocks
    # def print_status(self):
    #     occupied = {b: v for b, v in self.block_occupancy.items() if v is not None}

    #     if not occupied:
    #         return

    #     print("\nOccupied Blocks:")
    #     for b, v in occupied.items():
    #         print(f"{b}: {v}")

    # For debugging: print only when something changes
    def print_status_changes(self):
        changes = []

        for block in self.block_occupancy:
            old = self.previous_block_occupancy.get(block)
            new = self.block_occupancy.get(block)

            if old != new:
                changes.append((block, old, new))

        if not changes:
            return

        print("\nBlock Changes:")
        for block, old, new in changes:
            old_text = "FREE" if old is None else old
            new_text = "FREE" if new is None else new
            print(f"{block}: {old_text} -> {new_text}")