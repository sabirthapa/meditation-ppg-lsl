import simplepyble
from dataclasses import dataclass
from .._event import Event


@dataclass
class DeviceFoundEventArgs:
    Name: str
    Address: str
    AddressType: object
    Rssi: int
    peripheral: object


class BleDongle:
    def __init__(self):
        self._adapter = None
        self._peripheral = None
        self.DeviceFound = Event()
        self.Disconnected = Event()

    def Connect(self) -> bool:
        adapters = simplepyble.Adapter.get_adapters()
        if not adapters:
            return False
        self._adapter = adapters[0]
        return True

    def Disconnect(self) -> bool:
        if self._adapter:
            self._adapter.scan_stop()
        return True

    def StartScan(self) -> bool:
        if self._adapter is None:
            return False
        self._adapter.set_callback_on_scan_found(self._on_scan_found)
        self._adapter.scan_start()
        return True

    def StopScan(self) -> bool:
        if self._adapter:
            self._adapter.scan_stop()
        return True

    def ConnectToDevice(self, peripheral) -> object:
        """Connect to the given SimplePyBLE peripheral and return it."""
        try:
            peripheral.connect()
            self._peripheral = peripheral
            peripheral.set_callback_on_disconnected(self._on_disconnected)
            return peripheral
        except Exception:
            return None

    def DisconnectFromDevice(self) -> bool:
        if self._peripheral and self._peripheral.is_connected():
            self._peripheral.disconnect()
        self._peripheral = None
        return True

    @property
    def DeviceConnected(self) -> bool:
        return self._peripheral is not None and self._peripheral.is_connected()

    def LastRssi(self) -> int:
        return -128  # sbyte.MinValue equivalent

    def _on_scan_found(self, peripheral):
        args = DeviceFoundEventArgs(
            Name=peripheral.identifier(),
            Address=peripheral.address(),
            AddressType=peripheral.address_type(),
            Rssi=peripheral.rssi(),
            peripheral=peripheral,
        )
        self.DeviceFound(self, args)

    def _on_disconnected(self):
        self.Disconnected(self, None)
