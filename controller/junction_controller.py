import traci
from collections import deque

from utils.constants import (
    J1_TLS_ID,
    J1_STATES,
    ROUTE_REQUIREMENTS,
    TRAIN_ROUTE_EDGES,
    J1_RELEASE_ZONES,
)


class JunctionController:
    def __init__(self, block_controller):
        self.block_controller = block_controller
        self.requested_route = {}

        # one active owner of J1 at a time
        self.active_train = None
        self.active_route = None

        # FIFO queue for trains waiting for J1
        self.wait_queue = deque()

        self._set_j1("ALL_GREEN")

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

        # remove from queue if it is there
        self._remove_from_queue(train_id)

        self._set_j1(route_name)
        traci.vehicle.setRoute(train_id, TRAIN_ROUTE_EDGES[route_name])
        traci.vehicle.setSpeed(train_id, -1)

        print(f"{train_id}: granted {route_name}")

    def _hold(self, train_id, reason):
        traci.vehicle.setSpeed(train_id, 0)
        if self.active_train is None:
            self._set_j1("ALL_RED")
        print(f"{train_id}: waiting ({reason})")

    def _remove_from_queue(self, train_id):
        self.wait_queue = deque(t for t in self.wait_queue if t != train_id)

    def _is_j1_approach_block(self, current_block):
        return current_block in {"B2_up", "B3_down", "B5_down"}

    def _enqueue_if_needed(self, train_id, current_block):
        if not self._is_j1_approach_block(current_block):
            return

        if train_id == self.active_train:
            return

        if train_id not in self.wait_queue:
            self.wait_queue.append(train_id)
            print(f"{train_id}: added to J1 FIFO queue -> {list(self.wait_queue)}")

    def _cleanup_queue(self):
        """
        Remove trains that:
        - no longer exist in the simulation
        - are no longer waiting on a J1 approach block
        - are already the active train
        """
        existing = set(traci.vehicle.getIDList())
        cleaned = deque()

        for train_id in self.wait_queue:
            if train_id not in existing:
                continue

            if train_id == self.active_train:
                continue

            current_block = self.block_controller.get_train_block(train_id)
            if not self._is_j1_approach_block(current_block):
                continue

            if train_id not in cleaned:
                cleaned.append(train_id)

        self.wait_queue = cleaned

    def _is_queue_head(self, train_id):
        return len(self.wait_queue) > 0 and self.wait_queue[0] == train_id

    def _route_for_train(self, train_id, current_block):
        requested_route = self._get_requested_route(train_id)

        if current_block == "B2_up":
            if requested_route == "routeAB":
                return "A_to_B"
            elif requested_route == "routeAC":
                return "A_to_C"

        elif current_block == "B3_down":
            return "B_to_A"

        elif current_block == "B5_down":
            return "C_to_A"

        return None

    def _release_if_cleared(self, train_id, current_block):
        if self.active_train != train_id or self.active_route is None:
            return

        if current_block not in J1_RELEASE_ZONES[self.active_route]:
            print(f"{train_id}: released J1 route {self.active_route}")
            self.active_train = None
            self.active_route = None
            self._set_j1("ALL_RED")

    def control_train(self, train_id):
        current_block = self.block_controller.get_train_block(train_id)
        if current_block is None:
            return

        # first, release J1 if the owning train has cleared it
        self._release_if_cleared(train_id, current_block)

        # keep active train moving
        if self.active_train == train_id and self.active_route is not None:
            self._set_j1(self.active_route)
            traci.vehicle.setSpeed(train_id, -1)
            return

        # add approaching trains to FIFO queue
        self._enqueue_if_needed(train_id, current_block)

        # clean stale entries
        self._cleanup_queue()

        # if this train is not actually waiting for J1, nothing to do
        if not self._is_j1_approach_block(current_block):
            return

        # if another train owns J1, everybody else waits
        if self.active_train not in (None, train_id):
            self._hold(train_id, "J1 reserved")
            return

        # J1 is free now, but only the FIFO head may be granted
        if not self._is_queue_head(train_id):
            self._hold(train_id, f"FIFO waiting, head={self.wait_queue[0] if self.wait_queue else None}")
            return

        route_name = self._route_for_train(train_id, current_block)
        if route_name is None:
            self._hold(train_id, "unknown route")
            return

        if self._route_free(route_name):
            self._grant(train_id, route_name)
        else:
            self._hold(train_id, f"{route_name} blocks occupied")