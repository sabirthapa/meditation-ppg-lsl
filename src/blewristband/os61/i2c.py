from ..core.target_device import TargetDevice
from .message import Message


class I2C(TargetDevice):
    name = "I2C"

    def __init__(self, stream, i2c_address: int):
        super().__init__(stream, 2, "I2C")
        self._i2c_address = i2c_address

    @property
    def I2cAddress(self) -> int:
        return self._i2c_address

    def ReadRegister(self, register_address: int, number: int = 1) -> bytes:
        if number > 4:
            raise ValueError("Register read exceeds 4 bytes")
        frame = bytes([self._target_device_byte, 0, register_address, number, self._i2c_address])
        with TargetDevice._stream_lock:
            self._stream.write(frame)
            resp = self._stream.read()
        if resp[0] != Message.RegisterValue:
            raise RuntimeError("BLE response with unexpected data packet")
        # C# reads from index 4 down to (5 - number), reversed
        result = bytearray(number)
        for i in range(number):
            result[i] = resp[4 - i]
        return bytes(result)

    def ReadRegisterSingle(self, register_address: int) -> int:
        return self.ReadRegister(register_address, 1)[0]

    def ReadModifyWrite(self, register_address: int, stop: int, start: int, write_value: int) -> bool:
        frame = bytes([self._target_device_byte, 1, register_address, stop, start, write_value, self._i2c_address])
        with TargetDevice._stream_lock:
            return self._stream.write(frame)
