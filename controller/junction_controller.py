import traci
from collections import deque

from controller.sci_tds_protocol import (
    BLOCK_TO_TVPS_ID,
    TVPSOccupancyState,
    MsgTVPSOccupancyStatus,
    MsgTDPStatus,
    MsgAdditionalInformation,
    MsgCommandRejected,
    MsgTVPSFCPFailed,
    MsgTVPSFCPAFailed,
)

from utils.constants import (
    J1_TLS_ID,
    J1_STATES,
    ROUTE_REQUIREMENTS,
    TRAIN_ROUTE_EDGES,
    J1_RELEASE_ZONES,
)


class JunctionController:
    def __init__(self, block_controller, tds_object_controller, message_logger=None):
        self.block_controller = block_controller
        self.tds_object_controller = tds_object_controller
        self.message_logger = message_logger
        self.requested_route = {}

        self.section_state = {
            tvps_id: None
            for tvps_id in BLOCK_TO_TVPS_ID.values()
        }

        self.debug_tds = True

        self.active_train = None
        self.active_route = None
        self.wait_queue = deque()

        self._set_j1("ALL_RED")

    def _log_tds(self, text):
        if self.debug_tds:
            print(f"[EI ] {text}")

    def process_tds_messages(self):
        for msg in self.tds_object_controller.get_messages():
            if self.message_logger:
                self.message_logger.log_receive(msg)
                
            if isinstance(msg, MsgTVPSOccupancyStatus):
                self.section_state[msg.sender_id] = msg.occupancy_status
                self._log_tds(
                    f"TVPS {msg.sender_id} -> {msg.occupancy_status.name}, "
                    f"forceClear={msg.ability_to_be_forced_clear.name}, "
                    f"trigger={msg.change_trigger.name}"
                )

            elif isinstance(msg, MsgAdditionalInformation):
                self._log_tds(
                    f"ADD-INFO {msg.sender_id} speed={msg.speed_kmh} km/h "
                    f"wheel={msg.wheel_diameter_mm} mm"
                )

            elif isinstance(msg, MsgTDPStatus):
                self._log_tds(
                    f"TDP {msg.sender_id} state={msg.state_of_passing.name} "
                    f"direction={msg.direction_of_passing.name}"
                )

            elif isinstance(msg, MsgCommandRejected):
                self._log_tds(
                    f"COMMAND REJECTED by {msg.sender_id} reason={msg.reason.name}"
                )

            elif isinstance(msg, MsgTVPSFCPFailed):
                self._log_tds(
                    f"FC-P FAILED by {msg.sender_id} reason={msg.reason.name}"
                )

            elif isinstance(msg, MsgTVPSFCPAFailed):
                self._log_tds(
                    f"FC-P-A FAILED by {msg.sender_id} reason={msg.reason.name}"
                )

            else:
                self._log_tds(msg.summary())

    def _set_j1(self, route_name):
        traci.trafficlight.setRedYellowGreenState(J1_TLS_ID, J1_STATES[route_name])

    def _get_requested_route(self, train_id):
        if train_id not in self.requested_route:
            self.requested_route[train_id] = traci.vehicle.getRouteID(train_id)
        return self.requested_route[train_id]

    def _is_block_clear_via_tds(self, block_id):
        tvps_id = BLOCK_TO_TVPS_ID[block_id]
        state = self.section_state.get(tvps_id)

        if state == TVPSOccupancyState.VACANT:
            return True
        if state in (
            TVPSOccupancyState.OCCUPIED,
            TVPSOccupancyState.DISTURBED,
            TVPSOccupancyState.WAITING_SWEEPING_TRAIN,
            TVPSOccupancyState.WAITING_ACK_AFTER_FC_P_A,
            TVPSOccupancyState.SWEEPING_TRAIN_DETECTED,
        ):
            return False

        return self.block_controller.is_block_free(block_id)

    def _route_free(self, route_name):
        return all(
            self._is_block_clear_via_tds(block)
            for block in ROUTE_REQUIREMENTS[route_name]
        )

    def _grant(self, train_id, route_name):
        self.active_train = train_id
        self.active_route = route_name

        self._remove_from_queue(train_id)

        self._set_j1(route_name)
        traci.vehicle.setRoute(train_id, TRAIN_ROUTE_EDGES[route_name])
        traci.vehicle.setSpeed(train_id, -1)

        print(f"{train_id}: granted {route_name}")

    def _hold(self, train_id, reason):
        if self.active_train is None:
            self._set_j1("ALL_RED")

        traci.vehicle.setSpeed(train_id, -1)
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

    def _has_left_j1(self, current_block):
        if self.active_route == "A_to_B":
            return current_block == "B3_up"
        elif self.active_route == "A_to_C":
            return current_block == "B5_up"
        elif self.active_route == "B_to_A":
            return current_block == "B2_down"
        elif self.active_route == "C_to_A":
            return current_block == "B2_down"

        return False

    def control_train(self, train_id):
        current_block = self.block_controller.get_train_block(train_id)
        if current_block is None:
            return

        self._release_if_cleared(train_id, current_block)

        if self.active_train == train_id and self.active_route is not None:
            if self._has_left_j1(current_block):
                self._set_j1("ALL_RED")
            else:
                self._set_j1(self.active_route)

            traci.vehicle.setSpeed(train_id, -1)
            return

        self._enqueue_if_needed(train_id, current_block)
        self._cleanup_queue()

        if not self._is_j1_approach_block(current_block):
            return

        if self.active_train not in (None, train_id):
            self._hold(train_id, "J1 reserved")
            return

        if not self._is_queue_head(train_id):
            self._hold(
                train_id,
                f"FIFO waiting, head={self.wait_queue[0] if self.wait_queue else None}"
            )
            return

        route_name = self._route_for_train(train_id, current_block)
        if route_name is None:
            self._hold(train_id, "unknown route")
            return

        if self._route_free(route_name):
            self._grant(train_id, route_name)
        else:
            self._hold(train_id, f"{route_name} blocked by TVPS")