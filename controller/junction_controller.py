import traci

class JunctionController:

    def __init__(self, block_controller):
        self.block_controller = block_controller

    def control_train(self, train_id):
        current_block = self.block_controller.get_train_block(train_id)

        if current_block is None:
            return

        # -------------------------
        # 🚀 UP DIRECTION (A → J1)
        # -------------------------
        if current_block == "B2_up":

            # Try to go to B
            if self.block_controller.is_block_free("B3_up"):
                traci.vehicle.setRouteID(train_id, "route_to_B")
                traci.vehicle.setSpeed(train_id, -1)
                print(f"{train_id} → UP → B")

            # Else go to C
            elif self.block_controller.is_block_free("B5_up"):
                traci.vehicle.setRouteID(train_id, "route_to_C")
                traci.vehicle.setSpeed(train_id, -1)
                print(f"{train_id} → UP → C")

            else:
                # Stop before junction
                traci.vehicle.setSpeed(train_id, 0)
                print(f"{train_id} waiting at J1 (UP)")

        # -------------------------
        # 🔽 DOWN from B → J1 → A
        # -------------------------
        elif current_block == "B3_down":

            if self.block_controller.is_block_free("B2_down"):
                traci.vehicle.setSpeed(train_id, -1)
                print(f"{train_id} → DOWN → A")

            else:
                traci.vehicle.setSpeed(train_id, 0)
                print(f"{train_id} waiting (from B)")

        # -------------------------
        # 🔽 DOWN from C → J1 → A
        # -------------------------
        elif current_block == "B5_down":

            if self.block_controller.is_block_free("B2_down"):
                traci.vehicle.setSpeed(train_id, -1)
                print(f"{train_id} → DOWN → A")

            else:
                traci.vehicle.setSpeed(train_id, 0)
                print(f"{train_id} waiting (from C)")