import datetime
from ..core.target_device import TargetDevice
from .nrf_command import NrfCommand
from .message import Message


class NRF(TargetDevice):
    name = "NRF"

    def __init__(self, stream, target_device: int = 0):
        super().__init__(stream, target_device, "NRF")

    # ── write commands ────────────────────────────────────────────────────────

    def ConfigSensors(self) -> bool:
        return self._stream.write(bytes([0, 15, 0, 1, 16, 2]))

    def ConnectionParameters(self, setting: int) -> bool:
        return self._write_command(NrfCommand.ConnectionParameters, setting)

    def ConfigBBst(self, i_set: int, v_set: int) -> bool:
        return self._write_command(NrfCommand.ConfigBBst, i_set, v_set)

    def ConfigPmic(self, ap_data_out: bytes, op_code: int) -> bool:
        payload = bytes([len(ap_data_out)]) + ap_data_out + bytes([op_code])
        return self._write_command(NrfCommand.ConfigPmic, *payload)

    def ConfigVdd(self, setting: bool) -> bool:
        return self._write_command(NrfCommand.ConfigVdd, 1 if setting else 0)

    def ConfigVddLdo(self, setting: int) -> bool:
        return self._write_command(NrfCommand.ConfigVddLdo, setting)

    def ConfigVled(self, setting: bool) -> bool:
        return self._write_command(NrfCommand.ConfigVled, 1 if setting else 0)

    def EnableSensors(self, enable: bool) -> bool:
        return self._write_command(NrfCommand.EnableSensors, 1 if enable else 0)

    def EnableTestMode(self) -> bool:
        return self._write_command(17, 1)

    def RtcPrescale(self, setting: int) -> bool:
        return self._write_command(NrfCommand.RtcPrescale, setting)

    def UseAccelerometer(self, enable: bool, free_run: bool = True) -> bool:
        return self._write_command(
            NrfCommand.UseAccelerometer,
            1 if enable else 0,
            1 if free_run else 0,
        )

    # ── read commands ─────────────────────────────────────────────────────────

    def ReadBattery(self) -> int:
        return self._read_command(NrfCommand.Battery, Message.NrfBattery)[1]

    def ReadConfigVled(self) -> int:
        return self._read_command(NrfCommand.ConfigVled, Message.NrfConfigVLed)[1]

    def ReadConfigVdd(self) -> int:
        return self._read_command(NrfCommand.ConfigVdd, Message.NrfConfigVdd)[1]

    def ReadConfigVddLdo(self) -> int:
        return self._read_command(NrfCommand.ConfigVddLdo, Message.NrfConfigVddLdo)[1]

    def ReadConfigBBst(self) -> bytes:
        resp = self._read_command(NrfCommand.ConfigBBst, Message.NrfConfigBbst)
        return bytes([resp[1], resp[2]])

    def ReadConnectionParameters(self) -> int:
        return self._read_command(NrfCommand.ConnectionParameters, Message.NrfConnectionParameters)[1]

    def ReadEnableSensor(self) -> bool:
        return self._read_command(NrfCommand.EnableSensors, Message.EnableSensors)[1] == 1

    def ReadPhotoDiodes(self) -> int:
        return self._read_command(NrfCommand.NumPd, Message.NrfNumPd)[1]

    def ReadRtcPrescale(self) -> int:
        return self._read_command(NrfCommand.RtcPrescale, Message.NrfRtcPrescale)[1]

    def ReadUseAccelerometer(self) -> bool:
        return self._read_command(NrfCommand.UseAccelerometer, Message.NrfUseAccelerometer)[1] == 1

    def ReadUseAccelerometerBytes(self) -> bytes:
        resp = self._read_command(NrfCommand.UseAccelerometer, Message.NrfUseAccelerometer)
        return bytes([resp[1], resp[2], resp[3]])

    def ReadVersion(self) -> bytes:
        return self._read_command(NrfCommand.FirmwareVersion, Message.NrfFirmwareVersion)
