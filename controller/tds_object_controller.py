from collections import deque
import traci

from controller.sci_tds_protocol import (
    EI_TECHNICAL_ID,
    BLOCK_TO_TVPS_ID,
    TVPS_ID_TO_BLOCK,
    TDP_TRANSITIONS,
    CommandFC,
    CommandUpdateFillingLevel,
    CommandDRFC,
    CommandCancel,
    MsgTVPSOccupancyStatus,
    MsgCommandRejected,
    MsgTVPSFCPFailed,
    MsgTVPSFCPAFailed,
    MsgAdditionalInformation,
    MsgTDPStatus,
    FCMode,
    TVPSOccupancyState,
    ForceClearAbility,
    POMStatus,
    DisturbanceStatus,
    ChangeTrigger,
    CommandRejectedReason,
    FCPFailureReason,
    FCPAFailureReason,
    TDPPassingState,
    TDPDirection,
)


class TDSObjectController:
    """
    SCI-TDS object controller

    - TVPS status is derived from BlockController occupancy.
    - TDP status is derived from train edge transitions in SUMO.
    - Outbox contains SCI-TDS telegram objects.
    """

    def __init__(self, block_controller, ei_technical_id=EI_TECHNICAL_ID, message_logger=None):
        self.block_controller = block_controller
        self.ei_technical_id = ei_technical_id
        self.message_logger = message_logger

        self.debug = True
        self.outbox = deque()

        self.tvps_state = {
            tvps_id: None
            for tvps_id in TVPS_ID_TO_BLOCK
        }
        self.tvps_force_clear_ability = {
            tvps_id: ForceClearAbility.NOT_ABLE
            for tvps_id in TVPS_ID_TO_BLOCK
        }
        self.tvps_forced_clear_active = {
            tvps_id: False
            for tvps_id in TVPS_ID_TO_BLOCK
        }
        self.tvps_pending_fc_mode = {
            tvps_id: None
            for tvps_id in TVPS_ID_TO_BLOCK
        }

        self.prev_edge_by_train = {}
        self.tdp_initialized = {tdp_id: False for tdp_id in TDP_TRANSITIONS}

    def _log(self, text):
        if self.debug:
            print(f"[TDS] {text}")

    def get_messages(self):
        messages = list(self.outbox)
        self.outbox.clear()
        return messages

    def handle_command(self, telegram):
        if self.message_logger:
            self.message_logger.log_receive(telegram)
        if isinstance(telegram, CommandDRFC):
            self._handle_drfc(telegram)
        elif isinstance(telegram, CommandUpdateFillingLevel):
            self._handle_update_filling_level(telegram)
        elif isinstance(telegram, CommandFC):
            self._handle_fc(telegram)
        elif isinstance(telegram, CommandCancel):
            self._handle_cancel(telegram)

    def update(self):
        self._update_tvps()
        self._update_tdps()
        self._cleanup_train_memory()

    # --------------------------------------------------
    # TVPS handling
    # --------------------------------------------------
    def _handle_drfc(self, telegram: CommandDRFC):
        tvps_id = telegram.receiver_id
        if tvps_id not in TVPS_ID_TO_BLOCK:
            return

        self.tvps_force_clear_ability[tvps_id] = ForceClearAbility.ABLE
        self._emit_current_tvps_status(
            tvps_id,
            change_trigger=ChangeTrigger.COMMAND_FROM_EIL_ACCEPTED,
            include_filling_level=False,
        )

    def _handle_update_filling_level(self, telegram: CommandUpdateFillingLevel):
        tvps_id = telegram.receiver_id
        if tvps_id not in TVPS_ID_TO_BLOCK:
            return

        self._emit_current_tvps_status(
            tvps_id,
            change_trigger=ChangeTrigger.INTERNAL_TRIGGER,
            include_filling_level=True,
        )

    def _handle_fc(self, telegram: CommandFC):
        tvps_id = telegram.receiver_id
        if tvps_id not in TVPS_ID_TO_BLOCK:
            return

        mode = telegram.mode

        if mode in (FCMode.FC_U, FCMode.FC_C):
            if self.tvps_force_clear_ability[tvps_id] != ForceClearAbility.ABLE:
                self._emit(
                    MsgCommandRejected(
                        sender_id=tvps_id,
                        receiver_id=self.ei_technical_id,
                        reason=CommandRejectedReason.OPERATIONAL_REJECTED,
                    )
                )
                return

            self.tvps_forced_clear_active[tvps_id] = True
            self._emit_current_tvps_status(
                tvps_id,
                change_trigger=ChangeTrigger.COMMAND_FROM_EIL_ACCEPTED,
                include_filling_level=False,
            )
            return

        if mode == FCMode.FC_P:
            self.tvps_pending_fc_mode[tvps_id] = FCMode.FC_P
            self._emit(
                MsgTVPSFCPFailed(
                    sender_id=tvps_id,
                    receiver_id=self.ei_technical_id,
                    reason=FCPFailureReason.BOUNDING_TDP_NOT_PERMITTED,
                )
            )
            self.tvps_pending_fc_mode[tvps_id] = None
            return

        if mode == FCMode.FC_P_A:
            self.tvps_pending_fc_mode[tvps_id] = FCMode.FC_P_A
            self._emit(
                MsgTVPSFCPAFailed(
                    sender_id=tvps_id,
                    receiver_id=self.ei_technical_id,
                    reason=FCPAFailureReason.BOUNDING_TDP_NOT_PERMITTED,
                )
            )
            self.tvps_pending_fc_mode[tvps_id] = None
            return

        if mode == FCMode.ACK_AFTER_FC_P_A:
            self._emit(
                MsgCommandRejected(
                    sender_id=tvps_id,
                    receiver_id=self.ei_technical_id,
                    reason=CommandRejectedReason.OPERATIONAL_REJECTED,
                )
            )

    def _handle_cancel(self, telegram: CommandCancel):
        tvps_id = telegram.receiver_id
        if tvps_id not in TVPS_ID_TO_BLOCK:
            return

        pending_mode = self.tvps_pending_fc_mode[tvps_id]
        if pending_mode == FCMode.FC_P:
            self._emit(
                MsgTVPSFCPFailed(
                    sender_id=tvps_id,
                    receiver_id=self.ei_technical_id,
                    reason=FCPFailureReason.PROCESS_CANCELLED,
                )
            )
        elif pending_mode == FCMode.FC_P_A:
            self._emit(
                MsgTVPSFCPAFailed(
                    sender_id=tvps_id,
                    receiver_id=self.ei_technical_id,
                    reason=FCPAFailureReason.PROCESS_CANCELLED,
                )
            )
        else:
            self._emit(
                MsgCommandRejected(
                    sender_id=tvps_id,
                    receiver_id=self.ei_technical_id,
                    reason=CommandRejectedReason.OPERATIONAL_REJECTED,
                )
            )

        self.tvps_pending_fc_mode[tvps_id] = None

    def _update_tvps(self):
        for block_id, tvps_id in BLOCK_TO_TVPS_ID.items():
            current_state = self._effective_tvps_state(block_id, tvps_id)
            previous_state = self.tvps_state[tvps_id]

            if previous_state is None:
                self.tvps_state[tvps_id] = current_state
                self._emit_current_tvps_status(
                    tvps_id,
                    change_trigger=ChangeTrigger.INITIAL_SECTION_STATE,
                    include_filling_level=False,
                )
                continue

            if previous_state != current_state:
                self.tvps_state[tvps_id] = current_state
                self._emit_current_tvps_status(
                    tvps_id,
                    change_trigger=ChangeTrigger.PASSING_DETECTED,
                    include_filling_level=False,
                )
                self._emit_additional_information(tvps_id)

    def _effective_tvps_state(self, block_id, tvps_id):
        occupied = not self.block_controller.is_block_free(block_id)

        if self.tvps_forced_clear_active[tvps_id]:
            return TVPSOccupancyState.VACANT

        return TVPSOccupancyState.OCCUPIED if occupied else TVPSOccupancyState.VACANT

    def _current_filling_level(self, block_id):
        return 1 if not self.block_controller.is_block_free(block_id) else 0

    def _emit_current_tvps_status(self, tvps_id, change_trigger, include_filling_level):
        block_id = TVPS_ID_TO_BLOCK[tvps_id]
        state = self._effective_tvps_state(block_id, tvps_id)
        self.tvps_state[tvps_id] = state

        filling_level = self._current_filling_level(block_id) if include_filling_level else None

        self._emit(
            MsgTVPSOccupancyStatus(
                sender_id=tvps_id,
                receiver_id=self.ei_technical_id,
                occupancy_status=state,
                ability_to_be_forced_clear=self.tvps_force_clear_ability[tvps_id],
                filling_level=filling_level,
                pom_status=POMStatus.POWER_OK,
                disturbance_status=DisturbanceStatus.NOT_APPLICABLE,
                change_trigger=change_trigger,
            )
        )

    def _emit_additional_information(self, tvps_id):
        block_id = TVPS_ID_TO_BLOCK[tvps_id]
        train_id = self.block_controller.block_occupancy.get(block_id)

        speed_kmh = 0
        if train_id and train_id in traci.vehicle.getIDList():
            speed_ms = traci.vehicle.getSpeed(train_id)
            speed_kmh = max(0, min(9999, int(round(speed_ms * 3.6))))

        self._emit(
            MsgAdditionalInformation(
                sender_id=tvps_id,
                receiver_id=self.ei_technical_id,
                speed_kmh=speed_kmh,
                wheel_diameter_mm=840,
            )
        )

    # --------------------------------------------------
    # TDP handling
    # --------------------------------------------------
    def _update_tdps(self):
        current_trains = set(traci.vehicle.getIDList())

        for tdp_id, _transitions in TDP_TRANSITIONS.items():
            if not self.tdp_initialized[tdp_id]:
                self._emit(
                    MsgTDPStatus(
                        sender_id=tdp_id,
                        receiver_id=self.ei_technical_id,
                        state_of_passing=TDPPassingState.NOT_PASSED,
                        direction_of_passing=TDPDirection.WITHOUT_INDICATED_DIRECTION,
                    )
                )
                self.tdp_initialized[tdp_id] = True

        for train_id in current_trains:
            current_edge = traci.vehicle.getRoadID(train_id)
            previous_edge = self.prev_edge_by_train.get(train_id)

            if previous_edge and current_edge and previous_edge != current_edge:
                self._emit_matching_tdp_messages(previous_edge, current_edge)

            self.prev_edge_by_train[train_id] = current_edge

    def _emit_matching_tdp_messages(self, previous_edge, current_edge):
        transition = (previous_edge, current_edge)

        for tdp_id, mapping in TDP_TRANSITIONS.items():
            if transition in mapping:
                state_code, direction_code = mapping[transition]
                self._emit(
                    MsgTDPStatus(
                        sender_id=tdp_id,
                        receiver_id=self.ei_technical_id,
                        state_of_passing=TDPPassingState(state_code),
                        direction_of_passing=TDPDirection(direction_code),
                    )
                )

    def _cleanup_train_memory(self):
        existing = set(traci.vehicle.getIDList())
        self.prev_edge_by_train = {
            train_id: edge
            for train_id, edge in self.prev_edge_by_train.items()
            if train_id in existing
        }

    # --------------------------------------------------
    # output
    # --------------------------------------------------
    def _emit(self, telegram):
        self.outbox.append(telegram)

        if self.message_logger:
            self.message_logger.log_send(telegram)
        
        self._log(telegram.summary())