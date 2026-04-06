from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


PROTOCOL_TYPE = 0x20
SCI_TDS_PDI_VERSION = 0x02

EI_TECHNICAL_ID = "EI_01"

# Project mapping: logical blocks -> TVPS operational identifiers
BLOCK_TO_TVPS_ID = {
    "B1_up": "TVPS_B1_UP",
    "B1_down": "TVPS_B1_DOWN",
    "B2_up": "TVPS_B2_UP",
    "B2_down": "TVPS_B2_DOWN",
    "B3_up": "TVPS_B3_UP",
    "B3_down": "TVPS_B3_DOWN",
    "B4_up": "TVPS_B4_UP",
    "B4_down": "TVPS_B4_DOWN",
    "B5_up": "TVPS_B5_UP",
    "B5_down": "TVPS_B5_DOWN",
    "B6_up": "TVPS_B6_UP",
    "B6_down": "TVPS_B6_DOWN",
}
TVPS_ID_TO_BLOCK = {v: k for k, v in BLOCK_TO_TVPS_ID.items()}

# Project mapping: simple TDP operational identifiers
TDP_TRANSITIONS = {
    "TDP_A_B1": {
        ("E1", "E2"): (0x02, 0x01),      # passed, reference direction
        ("-E2", "-E1"): (0x02, 0x02),    # passed, against reference direction
    },
    "TDP_B1_B2": {
        ("E2", "E3"): (0x02, 0x01),
        ("-E3", "-E2"): (0x02, 0x02),
    },
    "TDP_B3_B4": {
        ("E4", "E5"): (0x02, 0x01),
        ("-E5", "-E4"): (0x02, 0x02),
    },
    "TDP_B5_B6": {
        ("E7", "E8"): (0x02, 0x01),
        ("-E8", "-E7"): (0x02, 0x02),
    },
}


class MessageType(IntEnum):
    FC = 0x0001
    UPDATE_FILLING_LEVEL = 0x0002
    DRFC = 0x0003
    COMMAND_REJECTED = 0x0006
    TVPS_OCCUPANCY_STATUS = 0x0007
    CANCEL = 0x0008
    TDP_STATUS = 0x000B
    TVPS_FC_P_FAILED = 0x0010
    TVPS_FC_P_A_FAILED = 0x0011
    ADDITIONAL_INFORMATION = 0x0012


class FCMode(IntEnum):
    FC_U = 0x01
    FC_C = 0x02
    FC_P_A = 0x03
    FC_P = 0x04
    ACK_AFTER_FC_P_A = 0x05


class TVPSOccupancyState(IntEnum):
    VACANT = 0x01
    OCCUPIED = 0x02
    DISTURBED = 0x03
    WAITING_SWEEPING_TRAIN = 0x04
    WAITING_ACK_AFTER_FC_P_A = 0x05
    SWEEPING_TRAIN_DETECTED = 0x06


class ForceClearAbility(IntEnum):
    NOT_ABLE = 0x01
    ABLE = 0x02


class POMStatus(IntEnum):
    POWER_OK = 0x01
    POWER_NOK = 0x02
    NOT_APPLICABLE = 0xFF


class DisturbanceStatus(IntEnum):
    OPERATIONAL = 0x01
    TECHNICAL = 0x02
    NOT_APPLICABLE = 0xFF


class ChangeTrigger(IntEnum):
    PASSING_DETECTED = 0x01
    COMMAND_FROM_EIL_ACCEPTED = 0x02
    COMMAND_FROM_MAINTAINER_ACCEPTED = 0x03
    TECHNICAL_FAILURE = 0x04
    INITIAL_SECTION_STATE = 0x05
    INTERNAL_TRIGGER = 0x06
    NOT_APPLICABLE = 0xFF


class CommandRejectedReason(IntEnum):
    OPERATIONAL_REJECTED = 0x01
    TECHNICAL_REJECTED = 0x02


class FCPFailureReason(IntEnum):
    INCORRECT_COUNT_SWEEPING_TRAIN = 0x01
    TIMEOUT = 0x02
    BOUNDING_TDP_NOT_PERMITTED = 0x03
    INTENTIONALLY_DELETED = 0x04
    OUTGOING_AXLE_BEFORE_MIN_TIMER = 0x05
    PROCESS_CANCELLED = 0x06


class FCPAFailureReason(IntEnum):
    INCORRECT_COUNT_SWEEPING_TRAIN = 0x01
    TIMEOUT = 0x02
    BOUNDING_TDP_NOT_PERMITTED = 0x03
    INTENTIONALLY_DELETED = 0x04
    OUTGOING_AXLE_BEFORE_MIN_TIMER = 0x05
    PROCESS_CANCELLED = 0x06


class TDPPassingState(IntEnum):
    NOT_PASSED = 0x01
    PASSED = 0x02
    DISTURBED = 0x03


class TDPDirection(IntEnum):
    REFERENCE_DIRECTION = 0x01
    AGAINST_REFERENCE_DIRECTION = 0x02
    WITHOUT_INDICATED_DIRECTION = 0x03


def _encode_id(identifier: str) -> bytes:
    raw = identifier.encode("latin-1", errors="replace")[:20]
    return raw.ljust(20, b" ")


def _u8(value: int) -> bytes:
    return int(value).to_bytes(1, byteorder="big", signed=False)


def _u16(value: int) -> bytes:
    return int(value).to_bytes(2, byteorder="big", signed=False)


def _s16(value: int) -> bytes:
    return int(value).to_bytes(2, byteorder="big", signed=True)


def _bcd16(value: int) -> bytes:
    if value < 0 or value > 9999:
        raise ValueError(f"BCD value out of range: {value}")
    digits = f"{value:04d}"
    return bytes([
        (int(digits[0]) << 4) | int(digits[1]),
        (int(digits[2]) << 4) | int(digits[3]),
    ])


@dataclass
class SCITDSTelegram:
    sender_id: str
    receiver_id: str
    message_type: MessageType

    def payload_bytes(self) -> bytes:
        return b""

    def to_bytes(self) -> bytes:
        return (
            _u8(PROTOCOL_TYPE)
            + _u16(int(self.message_type))
            + _encode_id(self.sender_id)
            + _encode_id(self.receiver_id)
            + self.payload_bytes()
        )

    def summary(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(type=0x{int(self.message_type):04X}, "
            f"sender={self.sender_id}, receiver={self.receiver_id})"
        )


@dataclass
class CommandFC(SCITDSTelegram):
    mode: FCMode = FCMode.FC_U

    def __init__(self, sender_id: str, receiver_id: str, mode: FCMode):
        super().__init__(sender_id, receiver_id, MessageType.FC)
        self.mode = mode

    def payload_bytes(self) -> bytes:
        return _u8(int(self.mode))


@dataclass
class CommandUpdateFillingLevel(SCITDSTelegram):
    def __init__(self, sender_id: str, receiver_id: str):
        super().__init__(sender_id, receiver_id, MessageType.UPDATE_FILLING_LEVEL)


@dataclass
class CommandDRFC(SCITDSTelegram):
    def __init__(self, sender_id: str, receiver_id: str):
        super().__init__(sender_id, receiver_id, MessageType.DRFC)


@dataclass
class CommandCancel(SCITDSTelegram):
    def __init__(self, sender_id: str, receiver_id: str):
        super().__init__(sender_id, receiver_id, MessageType.CANCEL)


@dataclass
class MsgTVPSOccupancyStatus(SCITDSTelegram):
    occupancy_status: TVPSOccupancyState
    ability_to_be_forced_clear: ForceClearAbility
    filling_level: Optional[int]
    pom_status: POMStatus
    disturbance_status: DisturbanceStatus
    change_trigger: ChangeTrigger

    def __init__(
        self,
        sender_id: str,
        receiver_id: str,
        occupancy_status: TVPSOccupancyState,
        ability_to_be_forced_clear: ForceClearAbility,
        filling_level: Optional[int] = None,
        pom_status: POMStatus = POMStatus.POWER_OK,
        disturbance_status: DisturbanceStatus = DisturbanceStatus.NOT_APPLICABLE,
        change_trigger: ChangeTrigger = ChangeTrigger.NOT_APPLICABLE,
    ):
        super().__init__(sender_id, receiver_id, MessageType.TVPS_OCCUPANCY_STATUS)
        self.occupancy_status = occupancy_status
        self.ability_to_be_forced_clear = ability_to_be_forced_clear
        self.filling_level = filling_level
        self.pom_status = pom_status
        self.disturbance_status = disturbance_status
        self.change_trigger = change_trigger

    def payload_bytes(self) -> bytes:
        filling = -1 if self.filling_level is None else int(self.filling_level)
        return (
            _u8(int(self.occupancy_status))
            + _u8(int(self.ability_to_be_forced_clear))
            + _s16(filling)
            + _u8(int(self.pom_status))
            + _u8(int(self.disturbance_status))
            + _u8(int(self.change_trigger))
        )


@dataclass
class MsgCommandRejected(SCITDSTelegram):
    reason: CommandRejectedReason

    def __init__(self, sender_id: str, receiver_id: str, reason: CommandRejectedReason):
        super().__init__(sender_id, receiver_id, MessageType.COMMAND_REJECTED)
        self.reason = reason

    def payload_bytes(self) -> bytes:
        return _u8(int(self.reason))


@dataclass
class MsgTVPSFCPFailed(SCITDSTelegram):
    reason: FCPFailureReason

    def __init__(self, sender_id: str, receiver_id: str, reason: FCPFailureReason):
        super().__init__(sender_id, receiver_id, MessageType.TVPS_FC_P_FAILED)
        self.reason = reason

    def payload_bytes(self) -> bytes:
        return _u8(int(self.reason))


@dataclass
class MsgTVPSFCPAFailed(SCITDSTelegram):
    reason: FCPAFailureReason

    def __init__(self, sender_id: str, receiver_id: str, reason: FCPAFailureReason):
        super().__init__(sender_id, receiver_id, MessageType.TVPS_FC_P_A_FAILED)
        self.reason = reason

    def payload_bytes(self) -> bytes:
        return _u8(int(self.reason))


@dataclass
class MsgAdditionalInformation(SCITDSTelegram):
    speed_kmh: int
    wheel_diameter_mm: int

    def __init__(self, sender_id: str, receiver_id: str, speed_kmh: int, wheel_diameter_mm: int):
        super().__init__(sender_id, receiver_id, MessageType.ADDITIONAL_INFORMATION)
        self.speed_kmh = speed_kmh
        self.wheel_diameter_mm = wheel_diameter_mm

    def payload_bytes(self) -> bytes:
        return _bcd16(int(self.speed_kmh)) + _bcd16(int(self.wheel_diameter_mm))


@dataclass
class MsgTDPStatus(SCITDSTelegram):
    state_of_passing: TDPPassingState
    direction_of_passing: TDPDirection

    def __init__(
        self,
        sender_id: str,
        receiver_id: str,
        state_of_passing: TDPPassingState,
        direction_of_passing: TDPDirection,
    ):
        super().__init__(sender_id, receiver_id, MessageType.TDP_STATUS)
        self.state_of_passing = state_of_passing
        self.direction_of_passing = direction_of_passing

    def payload_bytes(self) -> bytes:
        return _u8(int(self.state_of_passing)) + _u8(int(self.direction_of_passing))