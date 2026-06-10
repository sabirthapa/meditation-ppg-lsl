import threading


class TargetDevice:
    _stream_lock = threading.Lock()

    def __init__(self, stream, target_device: int, name: str):
        self._stream = stream
        self._target_device_byte = target_device
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    # C# capitalised alias
    @property
    def Name(self) -> str:
        return self._name

    def _read_command(self, command: int, message: int, extra: bytes = b"") -> bytes:
        """Write a read-request frame, then GATT-read the response."""
        frame = bytes([self._target_device_byte, command, 1]) + extra
        with TargetDevice._stream_lock:
            self._stream.write(frame)
            resp = self._stream.read()
        if resp is None:
            raise RuntimeError("Got a bad read")
        if resp[0] != message:
            raise RuntimeError(
                f"BLE response with unexpected data packet, "
                f"received {resp[0]} {resp[1] if len(resp) > 1 else '?'}, "
                f"expected {message}"
            )
        return resp

    def _command(self, command: int, message: int) -> bytes:
        """Two-byte command frame (no flag byte)."""
        frame = bytes([self._target_device_byte, command])
        with TargetDevice._stream_lock:
            self._stream.write(frame)
            resp = self._stream.read()
        if resp[0] != message:
            raise RuntimeError("BLE response with unexpected data packet")
        return resp

    def _write_command(self, command: int, *params: int) -> bool:
        frame = bytes([self._target_device_byte, command, 0, *params])
        with TargetDevice._stream_lock:
            return self._stream.write(frame)
