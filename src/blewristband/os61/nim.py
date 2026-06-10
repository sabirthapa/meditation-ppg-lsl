import datetime
from ..core.target_device import TargetDevice
from .nim_command import NimCommand
from .message import Message


class NIM(TargetDevice):
    name = "NIM"

    def __init__(self, stream, target_device: int = 1):
        super().__init__(stream, target_device, "NIM")
        self._stream = stream

    def EnableFclk(self, enable: bool) -> bool:
        return self._write_command(NimCommand.EnableFclk, 1 if enable else 0)

    def EnableFlashLog(self, enable: bool, name: str = "MAX86171") -> bool:
        now = datetime.datetime.now()
        name_bytes = bytearray(8)
        for i, c in enumerate(name[:8]):
            name_bytes[i] = ord(c)
        payload = bytes([
            1 if enable else 0,
            (now.year >> 16) & 0xFF,
            now.year & 0xFF,
            now.month,
            now.day,
            now.hour,
            now.month,   # matches C# (minute field uses month — preserved as-is)
            now.second,
            0,           # testFlash=False
            *name_bytes,
        ])
        return self._write_command(NimCommand.EnableFlashLog, *payload)

    def IsBusy(self) -> bool:
        return self._read_command(NimCommand.IsBusy, Message.NimIsBusy)[1] == 1

    def IsFull(self) -> bool:
        return self._read_command(NimCommand.IsFull, Message.NimIsFull)[1] == 1

    def ReadEnableFclk(self) -> bool:
        return self._read_command(NimCommand.EnableFclk, Message.NimEnableFclk)[1] == 1

    def ReadEnableFlashLog(self) -> bool:
        return self._read_command(NimCommand.EnableFlashLog, Message.EnableFlashLog)[1] == 1

    def ReadVersion(self) -> bytes:
        resp = b""
        while len(resp) < 7:
            resp = self._command(NimCommand.FirmwareVersion, Message.NimFirmwareVersion)
        return resp

    def WriteFlashLog(self, data: bytes) -> bool:
        if len(data) > 19:
            raise ValueError("WriteFlashLog: too many bytes for this packet")
        return self._write_command_flash(2, *data)

    # ── private helpers ───────────────────────────────────────────────────────

    def _write_command_flash(self, command: int, *params: int) -> bool:
        """NIM flash variant: no flag byte at index 2."""
        frame = bytes([self._target_device_byte, command, *params])
        with TargetDevice._stream_lock:
            return self._stream.write(frame)

    def _read_command(self, command, message) -> bytes:
        return super()._read_command(int(command), int(message))

    def _command(self, command, message) -> bytes:
        return super()._command(int(command), int(message))

    def _write_command(self, command, *params) -> bool:
        return super()._write_command(int(command), *params)
