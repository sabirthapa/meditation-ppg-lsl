import threading
from typing import List, Optional

from pylsl import local_clock


class PpgSession:
    """
    Handles raw BLE notifications from one OS61/MAXREFDES280 wristband.

    Responsibilities:
    - initialize optical registers
    - receive raw notification packets
    - parse 24-bit optical values
    - timestamp samples using LSL clock
    - optionally push parsed samples to an LSL outlet later
    """

    def __init__(self, participant_id: str, outlet=None):
        self.participant_id = participant_id
        self.outlet = outlet

        self.watch = None
        self.nrf = None
        self.nim = None
        self.optical = None

        self.buffers = {
            0: bytearray(),
            1: bytearray(),
        }

        self.samples: List[List[int]] = []
        self.timestamps: List[float] = []

        self.notification_count = 0
        self.ignored_notification_count = 0
        self.sample_count = 0

        self.lock = threading.Lock()

    def attach_devices(self, watch, nrf, nim, optical):
        self.watch = watch
        self.nrf = nrf
        self.nim = nim
        self.optical = optical

    def init_registers(self):
        if self.optical is None or self.nim is None:
            raise RuntimeError("Optical and NIM devices must be attached before init_registers().")

        # Copied from friend's PpgSession.init_registers()
        self.optical.ReadModifyWrite(12, 7, 0, 2)
        self.optical.ReadModifyWrite(13, 7, 0, 1)
        self.optical.ReadModifyWrite(14, 7, 0, 0)
        self.optical.ReadModifyWrite(15, 7, 0, 85)
        self.optical.ReadModifyWrite(16, 7, 0, 0)
        self.optical.ReadModifyWrite(17, 7, 0, 0)
        self.optical.ReadModifyWrite(21, 7, 0, 0)
        self.optical.ReadModifyWrite(22, 7, 0, 1)
        self.optical.ReadModifyWrite(23, 7, 0, 64)

        for slot in (24, 32, 40, 48, 56, 64, 72, 80, 88):
            self.optical.ReadModifyWrite(slot + 0, 7, 0, 0)
            self.optical.ReadModifyWrite(slot + 1, 7, 0, 24)
            self.optical.ReadModifyWrite(slot + 2, 7, 0, 58)
            self.optical.ReadModifyWrite(slot + 3, 7, 0, 80)
            self.optical.ReadModifyWrite(slot + 4, 7, 0, 10)
            self.optical.ReadModifyWrite(slot + 5, 7, 0, 0)
            self.optical.ReadModifyWrite(slot + 6, 7, 0, 0)

        self.optical.ReadModifyWrite(112, 7, 0, 0)
        self.nim.EnableFclk(False)

    def _parse_24bit_values(self, data: bytes) -> List[int]:
        values = []

        for i in range(0, len(data) - 2, 3):
            value = (data[i] << 16) | (data[i + 1] << 8) | data[i + 2]
            values.append(value)

        return values

    def _flush_sample(self, notify_type: int, data: bytes):
        values = self._parse_24bit_values(data)

        if not values:
            return

        timestamp = local_clock()

        # Keep a simple fixed-size sample for now.
        # Current raw packets usually produce 6 values from 18 payload bytes.
        while len(values) < 6:
            values.append(0)

        values = values[:6]

        with self.lock:
            self.samples.append(values)
            self.timestamps.append(timestamp)
            self.sample_count += 1

        if self.outlet is not None:
            # LSL sample channels are numeric.
            self.outlet.push_sample(values, timestamp)

    def on_notification(self, _sender, event):
        notify_type = getattr(event, "Notify", None)
        is_first = getattr(event, "First", False)
        raw_data = bytes(getattr(event, "Data", b""))

        with self.lock:
            self.notification_count += 1

        if notify_type not in (0, 1):
            with self.lock:
                self.ignored_notification_count += 1
            return

        if len(raw_data) < 3:
            return

        payload = raw_data[2:]
        buffer = self.buffers[notify_type]

        # In current tests, every packet is First=True and has 18 payload bytes.
        # If future firmware splits a sample over multiple packets, this keeps
        # the buffering behavior safe.
        if is_first and len(buffer) > 0:
            self._flush_sample(notify_type, bytes(buffer))
            buffer.clear()

        buffer.extend(payload)

        # Current observed packets have complete 18-byte payloads.
        # Flush immediately when we have at least 18 bytes.
        if len(buffer) >= 18:
            self._flush_sample(notify_type, bytes(buffer[:18]))
            del buffer[:18]

    def summary(self):
        with self.lock:
            return {
                "participant_id": self.participant_id,
                "notification_count": self.notification_count,
                "ignored_notification_count": self.ignored_notification_count,
                "sample_count": self.sample_count,
                "first_samples": self.samples[:5],
                "first_timestamps": self.timestamps[:5],
            }
