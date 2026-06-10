from .characteristic_stream import CharacteristicStream, SERVICE_UUID
from .._event import Event

STREAM_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"


class NotifyEventArgs:
    __slots__ = ("Data", "First")

    def __init__(self, data: bytes, first: bool):
        self.Data = data
        self.First = first

    @property
    def Notify(self) -> int:
        return self.Data[1]

    @property
    def PacketCount(self) -> int:
        return self.Data[0]


class WristbandSystem:
    def __init__(self, peripheral, dongle):
        self._peripheral = peripheral
        self._dongle = dongle
        self._config_stream = CharacteristicStream(peripheral)
        self._devices: dict = {}
        self._packet_count = 0
        self._first_time = True

        self.Disconnected = Event()
        self.NotificationAvailable = Event()
        self.Error = Event()

        dongle.Disconnected += self._on_dongle_disconnected

    @property
    def ReadWriteConfig(self) -> CharacteristicStream:
        return self._config_stream

    @property
    def Devices(self):
        return list(self._devices.values())

    def __getitem__(self, name: str):
        return self._devices.get(name)

    def AddTargetDevice(self, device) -> None:
        self._devices[device.name] = device

    def GetTargetDevice(self, name: str):
        return self._devices[name]

    def GetDevice(self, name: str):
        return self._devices[name]

    def EnableNotifications(self, enable: bool) -> bool:
        if enable:
            self._peripheral.notify(SERVICE_UUID, STREAM_UUID, self._on_raw_notification)
        else:
            self._peripheral.unsubscribe(SERVICE_UUID, STREAM_UUID)
        return True

    def LastRssi(self) -> int:
        return self._dongle.LastRssi()

    def Reset(self) -> None:
        self._packet_count = 0
        self._first_time = True

    def _on_raw_notification(self, data: bytes) -> None:
        for j in range(max(1, len(data) // 20)):
            offset = j * 20
            chunk = data[offset: offset + 20]
            if len(chunk) < 20:
                break

            b = chunk[0]
            if self._first_time:
                self._packet_count = b
                self._first_time = False

            if b != self._packet_count:
                dropped = b - self._packet_count
                if dropped < 1:
                    dropped += 256
                self.Error(self, {"message": f"Lost data packet {self._packet_count}", "dropped": dropped})
                self._packet_count = (b + 1) & 0xFF
            else:
                self._packet_count = (self._packet_count + 1) & 0xFF

            self.NotificationAvailable(self, NotifyEventArgs(data=bytes(chunk), first=(j == 0)))

    def _on_dongle_disconnected(self, sender, args) -> None:
        self.Disconnected(self, None)
