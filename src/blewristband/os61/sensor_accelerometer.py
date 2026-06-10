from dataclasses import dataclass
from .sensor import Sensor
from ..devices.accel_id import AccelID
from ..devices.accel_range import AccelRange


@dataclass
class BitField:
    address: int
    stop: int
    start: int


class SensorAccelerometer(Sensor):
    def __init__(self, stream, name: str = "ACCEL"):
        super().__init__(stream, 4, name)
        self.AccelName = name
        self.AccelID: AccelID = AccelID.NONE
        self.PartNumber: str = ""
        self.GRangeRegisterAddress: int = 0
        self.SupportedRange: list = []
        self.SupportedSampleRate: list = []
        self._range_reg_to_range: dict = {}
        self._range_to_reg: dict = {}
        self._sr_reg_to_value: dict = {}
        self._sr_value_to_reg: dict = {}
        self._range_field = BitField(0, 0, 0)
        self._sr_field = BitField(0, 0, 0)

    @property
    def GPerLsb(self) -> float:
        return 0.000244140625

    @property
    def SampleRateRegisterAddress(self) -> int:
        return self._sr_field.address

    def _add_range(self, reg_value: int, accel_range: AccelRange) -> None:
        self._range_reg_to_range[reg_value] = accel_range
        self._range_to_reg[accel_range] = reg_value

    def _add_sample_rate(self, reg_value: int, sr: float) -> None:
        self._sr_reg_to_value[reg_value] = sr
        self._sr_value_to_reg[sr] = reg_value

    def GetRange(self) -> AccelRange:
        raw = self.ReadRegisterSingle(self._range_field.address)
        bits = (raw >> self._range_field.start) & ((1 << (self._range_field.stop - self._range_field.start + 1)) - 1)
        return self._range_reg_to_range.get(bits, AccelRange.Reserved)

    def GetSampleRate(self) -> float:
        raw = self.ReadRegisterSingle(self._sr_field.address)
        return self._sr_reg_to_value.get(raw, 0.0)

    def SetRange(self, accel_range: AccelRange) -> None:
        reg_val = self._range_to_reg.get(accel_range)
        if reg_val is None:
            raise ValueError(f"Range {accel_range} not supported by {self.AccelName}")
        self.ReadModifyWrite(self._range_field.address, self._range_field.stop, self._range_field.start, reg_val)

    def SetSampleRate(self, sample_rate: float) -> None:
        reg_val = self._sr_value_to_reg.get(sample_rate)
        if reg_val is None:
            sorted_rates = sorted(self._sr_value_to_reg)
            next_rate = next((r for r in sorted_rates if r > sample_rate), None)
            if next_rate is None or next_rate not in self._sr_value_to_reg:
                raise ValueError(f"Sample rate {sample_rate} not supported by {self.AccelName}")
            reg_val = self._sr_value_to_reg[next_rate]
        self.ReadModifyWrite(self._sr_field.address, self._sr_field.stop, self._sr_field.start, reg_val)


# ── concrete accelerometer classes ────────────────────────────────────────────

class BMA280SensorAccelerometer(SensorAccelerometer):
    @property
    def GPerLsb(self) -> float:
        return 0.000244140625

    def __init__(self, stream):
        super().__init__(stream)
        self.AccelID = AccelID.BMA280
        self.PartNumber = "BMA280"
        for rv, ar in [(3, AccelRange.PM2g), (5, AccelRange.PM4g), (8, AccelRange.PM8g), (12, AccelRange.PM16g)]:
            self._add_range(rv, ar)
        self.SupportedRange = list(self._range_to_reg)
        for rv, sr in [(8, 15.62), (9, 31.26), (10, 62.5), (11, 125.0), (12, 250.0), (13, 500.0), (14, 1000.0), (15, 2000.0)]:
            self._add_sample_rate(rv, sr)
        self.SupportedSampleRate = list(self._sr_value_to_reg)
        for b in range(8):
            self._sr_reg_to_value[b] = 15.62
        for b in range(16, 32):
            self._sr_reg_to_value[b] = 2000.0
        self._range_field = BitField(15, 7, 0)
        self._sr_field    = BitField(16, 7, 0)
        self.GRangeRegisterAddress = 15


class KX122SensorAccelerometer(SensorAccelerometer):
    def __init__(self, stream):
        super().__init__(stream)
        self._kx_range = AccelRange.PM2g
        self.AccelID = AccelID.KX122
        self.PartNumber = "KX122-1037"
        for rv, ar in [(0, AccelRange.PM2g), (1, AccelRange.PM4g), (2, AccelRange.PM8g)]:
            self._add_range(rv, ar)
        self.SupportedRange = list(self._range_to_reg)
        for rv, sr in [(0, 12.5), (1, 25.0), (2, 50.0), (3, 100.0), (4, 200.0), (5, 400.0),
                       (6, 800.0), (7, 1600.0), (8, 0.781), (9, 1.563), (10, 3.125),
                       (11, 6.25), (12, 3200.0), (13, 6400.0), (14, 12800.0), (15, 25600.0)]:
            self._add_sample_rate(rv, sr)
        self.SupportedSampleRate = list(self._sr_value_to_reg)
        self.GRangeRegisterAddress = 24
        self._range_field = BitField(24, 4, 3)
        self._sr_field    = BitField(27, 3, 0)

    @property
    def GPerLsb(self) -> float:
        return {AccelRange.PM2g: 6.103515625e-05, AccelRange.PM4g: 0.0001220703125}.get(
            self._kx_range, 0.000244140625
        )


class KX132SensorAccelerometer(SensorAccelerometer):
    def __init__(self, stream):
        super().__init__(stream)
        self._kx_range = AccelRange.PM2g
        self.AccelID = AccelID.KX132
        self.PartNumber = "KX132-1211"
        for rv, ar in [(0, AccelRange.PM2g), (1, AccelRange.PM4g), (2, AccelRange.PM8g), (3, AccelRange.PM16g)]:
            self._add_range(rv, ar)
        self.SupportedRange = list(self._range_to_reg)
        for rv, sr in [(0, 0.781), (1, 1.563), (2, 3.125), (3, 6.25), (4, 12.5), (5, 25.0),
                       (6, 50.0), (7, 100.0), (8, 200.0), (9, 400.0), (10, 800.0),
                       (11, 1600.0), (12, 3200.0), (13, 6400.0), (14, 12800.0), (15, 25600.0)]:
            self._add_sample_rate(rv, sr)
        self.SupportedSampleRate = list(self._sr_value_to_reg)
        self.GRangeRegisterAddress = 24
        self._range_field = BitField(27, 4, 3)
        self._sr_field    = BitField(33, 3, 0)

    @property
    def GPerLsb(self) -> float:
        return {
            AccelRange.PM2g:  6.103515625e-05,
            AccelRange.PM4g:  0.0001220703125,
            AccelRange.PM8g:  0.000244140625,
            AccelRange.PM16g: 0.00048828125,
        }.get(self._kx_range, 0.000244140625)


class LIS2DS12SensorAccelerometer(SensorAccelerometer):
    def __init__(self, stream):
        super().__init__(stream)
        self._lis_range = AccelRange.PM2g
        self.AccelID = AccelID.LIS2DS12
        self.PartNumber = "LIS2DS12"
        for rv, ar in [(0, AccelRange.PM2g), (1, AccelRange.PM16g), (2, AccelRange.PM4g), (3, AccelRange.PM8g)]:
            self._add_range(rv, ar)
        self.SupportedRange = list(self._range_to_reg)
        for rv, sr in [(0, 0.0), (1, 12.5), (20, 25.0), (3, 50.0), (4, 100.0), (5, 200.0), (6, 400.0), (7, 800.0)]:
            self._add_sample_rate(rv, sr)
        self.SupportedSampleRate = list(self._sr_value_to_reg)
        self.GRangeRegisterAddress = 32
        self._range_field = BitField(32, 3, 2)
        self._sr_field    = BitField(32, 7, 4)

    @property
    def GPerLsb(self) -> float:
        return {
            AccelRange.PM2g:  6.103515625e-05,
            AccelRange.PM4g:  0.0001220703125,
            AccelRange.PM8g:  0.000244140625,
            AccelRange.PM16g: 0.00048828125,
        }.get(self._lis_range, 0.000244140625)


class NoneSensorAccelerometer(SensorAccelerometer):
    @property
    def GPerLsb(self) -> float:
        return 0.000244140625

    def __init__(self, stream):
        super().__init__(stream)
        self.AccelID = AccelID.NONE
        self.PartNumber = "None"
