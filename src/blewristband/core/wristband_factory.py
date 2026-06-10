from .wristband_system import WristbandSystem
from ..os61.nrf import NRF
from ..os61.nim import NIM
from ..os61.sensor_optical import SensorOptical
from ..os61.sensor_accelerometer import (
    BMA280SensorAccelerometer,
    KX122SensorAccelerometer,
    KX132SensorAccelerometer,
    LIS2DS12SensorAccelerometer,
    NoneSensorAccelerometer,
)
from ..os61.nrf_use_accel import NrfUseAccel
from ..os61.i2c import I2C
from ..devices.accel_id import AccelID


class WristbandFactory:
    def __init__(self, dongle):
        self._dongle = dongle
        self._system: WristbandSystem | None = None

    @property
    def WristbandSystem(self) -> WristbandSystem:
        return self._system

    def Connect(self, scan_info) -> bool:
        peripheral = self._dongle.ConnectToDevice(scan_info.peripheral)
        if peripheral is None:
            return False
        self._system = WristbandSystem(peripheral, self._dongle)
        return True

    def SetupOS61TargetDevices(self) -> WristbandSystem:
        stream = self._system.ReadWriteConfig
        nrf = NRF(stream, 0)
        nim = NIM(stream, 1)
        self._system.AddTargetDevice(nrf)
        self._system.AddTargetDevice(nim)

        read_bytes = nrf.ReadUseAccelerometerBytes()
        accel_info = NrfUseAccel(read_bytes)

        accel_map = {
            AccelID.BMA280:   BMA280SensorAccelerometer,
            AccelID.LIS2DS12: LIS2DS12SensorAccelerometer,
            AccelID.KX132:    KX132SensorAccelerometer,
            AccelID.KX122:    KX122SensorAccelerometer,
        }
        accel_cls = accel_map.get(accel_info.AccelID, NoneSensorAccelerometer)

        self._system.AddTargetDevice(SensorOptical(stream))
        self._system.AddTargetDevice(SensorOptical(stream, "OS62"))
        self._system.AddTargetDevice(accel_cls(stream))
        self._system.AddTargetDevice(I2C(stream, 40))
        return self._system
