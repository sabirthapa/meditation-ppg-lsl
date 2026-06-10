SERVICE_UUID = "6e400000-b5a3-f393-e0a9-e50e24dcca9e"
CONFIG_UUID  = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"


class CharacteristicStream:
    def __init__(self, peripheral):
        self._peripheral = peripheral

    def read(self) -> bytes:
        return self._peripheral.read(SERVICE_UUID, CONFIG_UUID)

    def write(self, data: bytes) -> bool:
        try:
            self._peripheral.write_request(SERVICE_UUID, CONFIG_UUID, data)
            return True
        except Exception:
            return False

    # Capitalized aliases to match C# call sites
    Read = read
    Write = write
