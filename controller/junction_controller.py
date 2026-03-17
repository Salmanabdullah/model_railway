import traci

from utils.constants import (
    J1_TLS_ID,
    J1_STATES,
    ROUTE_REQUIREMENTS,
    TRAIN_ROUTE_EDGES,
)


class JunctionController:
    def __init__(self, block_controller):
        self.block_controller = block_controller
        self.requested_route = {}

        # one active owner of J1 at a time
        self.active_train = None
        self.active_route = None

        self._set_j1("ALL_RED")

    def _set_j1(self, route_name):
        traci.trafficlight.setRedYellowGreenState(J1_TLS_ID, J1_STATES[route_name])

    def _get_requested_route(self, train_id):
        if train_id not in self.requested_route:
            self.requested_route[train_id] = traci.vehicle.getRouteID(train_id)
        return self.requested_route[train_id]

    def _route_free(self, route_name):
        return all(
            self.block_controller.is_block_free(block)
            for block in ROUTE_REQUIREMENTS[route_name]
        )

    def _grant(self, train_id, route_name):
        self.active_train = train_id
        self.active_route = route_name

        self._set_j1(route_name)
        traci.vehicle.setRoute(train_id, TRAIN_ROUTE_EDGES[route_name])
        traci.vehicle.setSpeed(train_id, -1)

        print(f"{train_id}: granted {route_name}")

    def _hold(self, train_id, reason):
        traci.vehicle.setSpeed(train_id, 0)
        if self.active_train is None:
            self._set_j1("ALL_RED")
        print(f"{train_id}: waiting ({reason})")

    def _release_if_cleared(self, train_id, current_block):
        if self.active_train != train_id:
            return

        if self.active_route == "A_to_B" and current_block not in {"B2_up", "B3_up"}:
            self.active_train = None
            self.active_route = None
            self._set_j1("ALL_RED")

        elif self.active_route == "A_to_C" and current_block not in {"B2_up", "B5_up"}:
            self.active_train = None
            self.active_route = None
            self._set_j1("ALL_RED")

        elif self.active_route == "B_to_A" and current_block not in {"B3_down", "B2_down"}:
            self.active_train = None
            self.active_route = None
            self._set_j1("ALL_RED")

        elif self.active_route == "C_to_A" and current_block not in {"B5_down", "B2_down"}:
            self.active_train = None
            self.active_route = None
            self._set_j1("ALL_RED")

    def control_train(self, train_id):
        current_block = self.block_controller.get_train_block(train_id)
        if current_block is None:
            return

        self._release_if_cleared(train_id, current_block)

        if self.active_train not in (None, train_id):
            if current_block in {"B2_up", "B3_down", "B5_down"}:
                self._hold(train_id, "J1 reserved")
            return

        requested_route = self._get_requested_route(train_id)

        if current_block == "B2_up":
            if requested_route == "routeAB":
                if self._route_free("A_to_B"):
                    self._grant(train_id, "A_to_B")
                else:
                    self._hold(train_id, "A_to_B blocks occupied")

            elif requested_route == "routeAC":
                if self._route_free("A_to_C"):
                    self._grant(train_id, "A_to_C")
                else:
                    self._hold(train_id, "A_to_C blocks occupied")

            else:
                self._hold(train_id, f"unknown requested route {requested_route}")

        elif current_block == "B3_down":
            if self._route_free("B_to_A"):
                self._grant(train_id, "B_to_A")
            else:
                self._hold(train_id, "B_to_A blocks occupied")

        elif current_block == "B5_down":
            if self._route_free("C_to_A"):
                self._grant(train_id, "C_to_A")
            else:
                self._hold(train_id, "C_to_A blocks occupied")