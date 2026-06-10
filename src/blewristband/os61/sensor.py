from ..core.target_device import TargetDevice
from .message import Message


class Sensor(TargetDevice):
    def __init__(self, stream, target_device: int, name: str):
        super().__init__(stream, target_device, name)

    def ReadRegister(self, register_address: int, number: int = 1):
        if number > 4:
            raise ValueError("Register read exceeds 4 bytes")
        frame = bytes([self._target_device_byte, 0, register_address, number])
        with TargetDevice._stream_lock:
            self._stream.write(frame)
            resp = self._stream.read()
        if resp is None:
            raise RuntimeError("Got a bad register read.")
        if resp[0] != Message.RegisterValue:
            raise RuntimeError("BLE response with unexpected data packet")
        if number == 1:
            # Single-byte read: C# returns resp[1:5] and caller takes index [3]
            return resp[1:5]
        return bytes(resp[1:5])

    def ReadRegisterSingle(self, register_address: int) -> int:
        """Returns the single byte value; mirrors C# ReadRegister(addr) → byte."""
        return self.ReadRegister(register_address, 1)[3]

    def ReadRegisterBlock(self, register_address: int, length: int) -> bytes:
        if length > 19:
            raise ValueError("Register read exceeds length of 19")
        frame = bytes([self._target_device_byte, 2, register_address, length])
        with TargetDevice._stream_lock:
            self._stream.write(frame)
            resp = self._stream.read()
        if resp is None:
            raise RuntimeError("Register block read failed to return result")
        if resp[0] != Message.RegBlockRead:
            raise RuntimeError("BLE response with unexpected data packet")
        return bytes(resp[1: 1 + length])

    def ReadModifyWrite(
        self,
        register_address: int,
        stop: int,
        start: int,
        write_value: int,
    ) -> bool:
        frame = bytes([self._target_device_byte, 1, register_address, stop, start, write_value])
        with TargetDevice._stream_lock:
            return self._stream.write(frame)
