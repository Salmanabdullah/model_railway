from controller.sci_tds_protocol import (
    PROTOCOL_TYPE,
    MessageType,
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
)


MESSAGE_TYPE_LABELS = {
    MessageType.FC: "FC",
    MessageType.UPDATE_FILLING_LEVEL: "Update Filling Level",
    MessageType.DRFC: "DRFC",
    MessageType.COMMAND_REJECTED: "Command Rejected",
    MessageType.TVPS_OCCUPANCY_STATUS: "TVPS Occupancy Status",
    MessageType.CANCEL: "Cancel",
    MessageType.TDP_STATUS: "TDP Status",
    MessageType.TVPS_FC_P_FAILED: "TVPS FC-P failed",
    MessageType.TVPS_FC_P_A_FAILED: "TVPS FC-P-A failed",
    MessageType.ADDITIONAL_INFORMATION: "Additional Information",
}


def _enum_text(value):
    if value is None:
        return "None"

    if hasattr(value, "name"):
        return f"0x{int(value):02X} ({value.name})"

    if isinstance(value, int):
        return f"0x{value:02X}"

    return str(value)


def _fmt_line(byte_range: str, field_name: str, value: str) -> str:
    return f"{byte_range:<9} {field_name:<28} {value}"


def decode_telegram_fields(telegram) -> str:
    lines = []

    msg_type = telegram.message_type
    msg_label = MESSAGE_TYPE_LABELS.get(msg_type, "Unknown")

    # common SCI-TDS header
    lines.append(_fmt_line("[00]", "Protocol Type", f"0x{PROTOCOL_TYPE:02X}"))
    lines.append(_fmt_line("[01..02]", "Message Type", f"0x{int(msg_type):04X} ({msg_label})"))
    lines.append(_fmt_line("[03..22]", "Sender Identifier", telegram.sender_id))
    lines.append(_fmt_line("[23..42]", "Receiver Identifier", telegram.receiver_id))

    # subsystem-specific payload
    if isinstance(telegram, CommandFC):
        lines.append(_fmt_line("[43]", "Mode of FC", _enum_text(telegram.mode)))

    elif isinstance(telegram, CommandUpdateFillingLevel):
        pass

    elif isinstance(telegram, CommandDRFC):
        pass

    elif isinstance(telegram, CommandCancel):
        pass

    elif isinstance(telegram, MsgTVPSOccupancyStatus):
        filling = "0xFFFF (not applicable)" if telegram.filling_level is None else str(telegram.filling_level)
        lines.append(_fmt_line("[43]", "Occupancy Status", _enum_text(telegram.occupancy_status)))
        lines.append(_fmt_line("[44]", "Ability to force clear", _enum_text(telegram.ability_to_be_forced_clear)))
        lines.append(_fmt_line("[45..46]", "Filling Level", filling))
        lines.append(_fmt_line("[47]", "POM Status", _enum_text(telegram.pom_status)))
        lines.append(_fmt_line("[48]", "Disturbance Status", _enum_text(telegram.disturbance_status)))
        lines.append(_fmt_line("[49]", "Change Trigger", _enum_text(telegram.change_trigger)))

    elif isinstance(telegram, MsgCommandRejected):
        lines.append(_fmt_line("[43]", "Reason for Rejection", _enum_text(telegram.reason)))

    elif isinstance(telegram, MsgTVPSFCPFailed):
        lines.append(_fmt_line("[43]", "Reason for failure", _enum_text(telegram.reason)))

    elif isinstance(telegram, MsgTVPSFCPAFailed):
        lines.append(_fmt_line("[43]", "Reason for failure", _enum_text(telegram.reason)))

    elif isinstance(telegram, MsgAdditionalInformation):
        lines.append(_fmt_line("[43..44]", "Speed (km/h BCD)", str(telegram.speed_kmh)))
        lines.append(_fmt_line("[45..46]", "Wheel Diameter (mm BCD)", str(telegram.wheel_diameter_mm)))

    elif isinstance(telegram, MsgTDPStatus):
        lines.append(_fmt_line("[43]", "State of passing", _enum_text(telegram.state_of_passing)))
        lines.append(_fmt_line("[44]", "Direction of passing", _enum_text(telegram.direction_of_passing)))

    else:
        lines.append(_fmt_line("[..]", "Decoder", "No field decoder available"))

    return "\n".join(lines)