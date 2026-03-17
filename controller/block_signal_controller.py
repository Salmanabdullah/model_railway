import traci

from utils.constants import ROUTE_REQUIREMENTS


class BlockSignalController:
    """
    Controls all six block signals:
        B1 -> TLS1
        B2 -> TLS2
        B3 -> TLS3
        B4 -> TLS4
        B5 -> TLS5
        B6 -> TLS6

    Net-confirmed link order for TLS1..TLS6:
        link 0 = down direction
        link 1 = up direction
    """

    TLS = {
        "B1": "TLS1",
        "B2": "TLS2",
        "B3": "TLS3",
        "B4": "TLS4",
        "B5": "TLS5",
        "B6": "TLS6",
    }

    def __init__(self, block_controller, junction_controller):
        self.block_controller = block_controller
        self.junction_controller = junction_controller

    # --------------------------------------------------
    # low-level helpers
    # --------------------------------------------------
    def _set(self, tls_id, down_aspect, up_aspect):
        """
        down_aspect -> link 0
        up_aspect   -> link 1
        """
        state = f"{down_aspect}{up_aspect}"
        traci.trafficlight.setRedYellowGreenState(tls_id, state)

    def _vehicle_on_edge(self, edge_id):
        vehicles = traci.edge.getLastStepVehicleIDs(edge_id)
        return vehicles[0] if vehicles else None

    def _get_requested_route(self, train_id):
        # prefer the cached original route from junction_controller if available
        cached = getattr(self.junction_controller, "requested_route", {})
        if train_id in cached:
            return cached[train_id]

        return traci.vehicle.getRouteID(train_id)

    def _active_train(self):
        return getattr(self.junction_controller, "active_train", None)

    def _route_free(self, route_name):
        return all(
            self.block_controller.is_block_free(block)
            for block in ROUTE_REQUIREMENTS[route_name]
        )

    def _j1_reserved_for_other(self, train_id):
        active = self._active_train()
        return active not in (None, train_id)

    # --------------------------------------------------
    # aspect decisions for signals close to J1
    # --------------------------------------------------
    def _aspect_b2_up(self):
        """
        TLS2 up direction: E2 -> E3
        This is the A-side approach signal before J1.
        Show:
            G = proceed toward J1
            y = expect stop at J1
            r = next block B2_up occupied
        """
        # E3 is B2_up
        if not self.block_controller.is_block_free("B2_up"):
            return "r"

        train_id = self._vehicle_on_edge("E2")

        # no train immediately approaching: keep it permissive if any A route is available
        if train_id is None:
            if self._route_free("A_to_B") or self._route_free("A_to_C"):
                return "G"
            return "y"

        requested = self._get_requested_route(train_id)

        if self._j1_reserved_for_other(train_id):
            return "y"

        if requested == "routeAB":
            return "G" if self._route_free("A_to_B") else "y"

        if requested == "routeAC":
            return "G" if self._route_free("A_to_C") else "y"

        return "y"

    def _aspect_b3_down(self):
        """
        TLS3 down direction: -E5 -> -E4
        This is the B-side approach signal before J1.
        Show:
            G = proceed toward J1
            y = expect stop at J1
            r = next block B3_down occupied
        """
        # -E4 is B3_down
        if not self.block_controller.is_block_free("B3_down"):
            return "r"

        train_id = self._vehicle_on_edge("-E5")

        if train_id is None:
            return "G" if self._route_free("B_to_A") else "y"

        if self._j1_reserved_for_other(train_id):
            return "y"

        return "G" if self._route_free("B_to_A") else "y"

    def _aspect_b5_down(self):
        """
        TLS5 down direction: -E8 -> -E7
        This is the C-side approach signal before J1.
        Show:
            G = proceed toward J1
            y = expect stop at J1
            r = next block B5_down occupied
        """
        # -E7 is B5_down
        if not self.block_controller.is_block_free("B5_down"):
            return "r"

        train_id = self._vehicle_on_edge("-E8")

        if train_id is None:
            return "G" if self._route_free("C_to_A") else "y"

        if self._j1_reserved_for_other(train_id):
            return "y"

        return "G" if self._route_free("C_to_A") else "y"

    # --------------------------------------------------
    # main update
    # --------------------------------------------------
    def update(self):
        """
        Called once per simulation step, after block occupancy is updated.
        """

        # --------------------------------------------------
        # B1 / TLS1
        # link 0: -E2 -> -E1  (down)
        # link 1:  E1 -> E2   (up)
        #
        # Up direction enters B1_up (E2)
        # Down direction goes into terminal A
        # --------------------------------------------------
        b1_down = "G"
        b1_up = "G" if self.block_controller.is_block_free("B1_up") else "r"
        self._set(self.TLS["B1"], b1_down, b1_up)

        # --------------------------------------------------
        # B2 / TLS2
        # link 0: -E3 -> -E2  (down)
        # link 1:  E2 -> E3   (up)
        #
        # Down direction enters B1_down (-E2)
        # Up direction is the approach warning signal before J1 from A
        # --------------------------------------------------
        b2_down = "G" if self.block_controller.is_block_free("B1_down") else "r"
        b2_up = self._aspect_b2_up()
        self._set(self.TLS["B2"], b2_down, b2_up)

        # --------------------------------------------------
        # B3 / TLS3
        # link 0: -E5 -> -E4  (down)
        # link 1:  E4 -> E5   (up)
        #
        # Up direction enters B4_up (E5)
        # Down direction is the approach warning signal before J1 from B
        # --------------------------------------------------
        b3_down = self._aspect_b3_down()
        b3_up = "G" if self.block_controller.is_block_free("B4_up") else "r"
        self._set(self.TLS["B3"], b3_down, b3_up)

        # --------------------------------------------------
        # B4 / TLS4
        # link 0: -E6 -> -E5  (down)
        # link 1:  E5 -> E6   (up)
        #
        # Down direction enters B4_down (-E5)
        # Up direction goes into terminal B
        # --------------------------------------------------
        b4_down = "G" if self.block_controller.is_block_free("B4_down") else "r"
        b4_up = "G"
        self._set(self.TLS["B4"], b4_down, b4_up)

        # --------------------------------------------------
        # B5 / TLS5
        # link 0: -E8 -> -E7  (down)
        # link 1:  E7 -> E8   (up)
        #
        # Up direction enters B6_up (E8)
        # Down direction is the approach warning signal before J1 from C
        # --------------------------------------------------
        b5_down = self._aspect_b5_down()
        b5_up = "G" if self.block_controller.is_block_free("B6_up") else "r"
        self._set(self.TLS["B5"], b5_down, b5_up)

        # --------------------------------------------------
        # B6 / TLS6
        # link 0: -E9 -> -E8  (down)
        # link 1:  E8 -> E9   (up)
        #
        # Down direction enters B6_down (-E8)
        # Up direction goes into terminal C
        # --------------------------------------------------
        b6_down = "G" if self.block_controller.is_block_free("B6_down") else "r"
        b6_up = "G"
        self._set(self.TLS["B6"], b6_down, b6_up)