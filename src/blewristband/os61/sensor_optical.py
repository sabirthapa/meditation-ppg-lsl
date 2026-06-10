from enum import IntEnum
from .sensor import Sensor


class PartNumber(IntEnum):
    Unread     = 0
    Unknown    = 1
    Unreleased = 2
    MAX86171   = 44
    MAX86172   = 72
    MAX86173   = 67


class SensorOptical(Sensor):
    name = "OS61"

    def __init__(self, stream, optical_name: str = "OS61"):
        super().__init__(stream, 3, optical_name)
        self._part_number = PartNumber.Unread

    @property
    def Part(self) -> PartNumber:
        return self._part_number

    def ReadPartID(self) -> PartNumber:
        val = self.ReadRegisterSingle(0xFF)
        try:
            self._part_number = PartNumber(val)
        except ValueError:
            self._part_number = PartNumber.Unknown
        return self._part_number
