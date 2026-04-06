from controller.traci_manager import start_simulation, simulation_step, close_simulation
from controller.block_controller import BlockController
from controller.tds_object_controller import TDSObjectController
from controller.junction_controller import JunctionController
from controller.train_controller import TrainController
from controller.block_signal_controller import BlockSignalController
from controller.sci_tds_logger import SCITDSMessageLogger
from controller.sci_tds_protocol import (
    EI_TECHNICAL_ID,
    CommandDRFC,
    CommandUpdateFillingLevel,
)

CONFIG = "config/rail.sumocfg"


def send_tds_command(tds_object_controller, message_logger, telegram):
    if message_logger:
        message_logger.log_send(telegram)
    tds_object_controller.handle_command(telegram)


def run():
    start_simulation(CONFIG)

    message_logger = SCITDSMessageLogger(
        hex_dump_to_console=False,
        hex_dump_to_file=True,
        decoded_fields_to_console=True,
        decoded_fields_to_file=True,
        console_filter={
            "MsgTVPSOccupancyStatus",
            "MsgTDPStatus",
            "CommandFC",
            "CommandDRFC",
            "CommandUpdateFillingLevel",
            "CommandCancel",
            "MsgCommandRejected",
            "MsgTVPSFCPFailed",
            "MsgTVPSFCPAFailed",
            "MsgAdditionalInformation",
        },

    )
    message_logger.log_info("SCI-TDS logging started")

    block_controller = BlockController()
    tds_object_controller = TDSObjectController(
        block_controller,
        message_logger=message_logger,
    )
    junction_controller = JunctionController(
        block_controller,
        tds_object_controller,
        message_logger=message_logger,
    )
    block_signal_controller = BlockSignalController(block_controller, junction_controller)
    train_controller = TrainController(block_controller, junction_controller)

    # Example startup commands from EI to TDS
    send_tds_command(
        tds_object_controller,
        message_logger,
        CommandDRFC(sender_id=EI_TECHNICAL_ID, receiver_id="TVPS_B5_DOWN"),
    )
    send_tds_command(
        tds_object_controller,
        message_logger,
        CommandUpdateFillingLevel(sender_id=EI_TECHNICAL_ID, receiver_id="TVPS_B5_DOWN"),
    )

    step = 0
    while step < 300:
        simulation_step()

        block_controller.update_occupancy()
        tds_object_controller.update()
        junction_controller.process_tds_messages()
        train_controller.update_trains()
        block_signal_controller.update()

        block_controller.print_status_changes()

        step += 1

    message_logger.log_info("SCI-TDS logging finished")
    close_simulation()


if __name__ == "__main__":
    run()