from pathlib import Path
from datetime import datetime
import csv

from controller.hex_dump_viewer import format_hex_dump
from controller.sci_tds_decoder import decode_telegram_fields


class SCITDSMessageLogger:
    def __init__(
        self,
        log_dir="logs",
        session_name=None,
        enabled=True,
        hex_dump_to_console=True,
        hex_dump_to_file=True,
        decoded_fields_to_console=True,
        decoded_fields_to_file=True,
        console_filter=None,
        events_to_log=None,
        classes_to_log=None,
    ):
        self.enabled = enabled
        self.hex_dump_to_console = hex_dump_to_console
        self.hex_dump_to_file = hex_dump_to_file
        self.decoded_fields_to_console = decoded_fields_to_console
        self.decoded_fields_to_file = decoded_fields_to_file

        self.console_filter = set(console_filter) if console_filter else None
        self.events_to_log = set(events_to_log) if events_to_log else None
        self.classes_to_log = set(classes_to_log) if classes_to_log else None

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        if session_name is None:
            session_name = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.session_name = session_name
        self.text_path = self.log_dir / f"sci_tds_{session_name}.log"
        self.csv_path = self.log_dir / f"sci_tds_{session_name}.csv"

        self._init_csv()

    def _init_csv(self):
        if not self.csv_path.exists():
            with self.csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp",
                    "event",
                    "telegram_class",
                    "message_type_hex",
                    "sender_id",
                    "receiver_id",
                    "summary",
                    "hex_bytes",
                ])

    def _should_log(self, event, telegram):
        if self.events_to_log is not None and event not in self.events_to_log:
            return False

        if self.classes_to_log is not None and telegram.__class__.__name__ not in self.classes_to_log:
            return False

        return True

    def _telegram_raw_hex(self, telegram):
        try:
            return telegram.to_bytes().hex(" ").upper()
        except Exception as exc:
            return f"<hex-error: {exc}>"

    def _telegram_dump(self, telegram):
        try:
            raw_bytes = telegram.to_bytes()
            return format_hex_dump(raw_bytes)
        except Exception as exc:
            return f"<dump-error: {exc}>"

    def _telegram_decoded(self, telegram):
        try:
            return decode_telegram_fields(telegram)
        except Exception as exc:
            return f"<decode-error: {exc}>"

    def _summary(self, telegram):
        try:
            return telegram.summary()
        except Exception:
            telegram_class = telegram.__class__.__name__
            message_type_hex = f"0x{int(telegram.message_type):04X}"
            return (
                f"{telegram_class}(type={message_type_hex}, "
                f"sender={getattr(telegram, 'sender_id', '?')}, "
                f"receiver={getattr(telegram, 'receiver_id', '?')})"
            )

    def _should_console_show_details(self, telegram):
        if self.console_filter is None:
            return True
        return telegram.__class__.__name__ in self.console_filter

    def log(self, event, telegram):
        if not self.enabled:
            return

        if not self._should_log(event, telegram):
            return

        timestamp = datetime.now().isoformat(timespec="milliseconds")
        telegram_class = telegram.__class__.__name__
        message_type_hex = f"0x{int(telegram.message_type):04X}"
        summary = self._summary(telegram)
        raw_hex = self._telegram_raw_hex(telegram)
        dump = self._telegram_dump(telegram)
        decoded = self._telegram_decoded(telegram)

        line = f"{timestamp} | {event:<10} | {summary} | HEX={raw_hex}"

        with self.text_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

            if self.hex_dump_to_file:
                f.write("--- HEX DUMP ---\n")
                f.write(dump + "\n")

            if self.decoded_fields_to_file:
                f.write("--- FIELD DECODER ---\n")
                f.write(decoded + "\n")

            f.write("\n")

        with self.csv_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                event,
                telegram_class,
                message_type_hex,
                getattr(telegram, "sender_id", ""),
                getattr(telegram, "receiver_id", ""),
                summary,
                raw_hex,
            ])

        print(line)

        if self._should_console_show_details(telegram):
            if self.hex_dump_to_console:
                print("--- HEX DUMP ---")
                print(dump)

            if self.decoded_fields_to_console:
                print("--- FIELD DECODER ---")
                print(decoded)

            if self.hex_dump_to_console or self.decoded_fields_to_console:
                print()

    def log_send(self, telegram):
        self.log("SEND", telegram)

    def log_receive(self, telegram):
        self.log("RECV", telegram)

    def log_info(self, text):
        if not self.enabled:
            return

        timestamp = datetime.now().isoformat(timespec="milliseconds")
        line = f"{timestamp} | INFO       | {text}"

        with self.text_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

        print(line)