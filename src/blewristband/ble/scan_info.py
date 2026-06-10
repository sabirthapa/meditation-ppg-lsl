class BleScanInfo:
    """Wraps a SimplePyBLE peripheral discovered during a scan."""

    def __init__(self, peripheral):
        self._peripheral = peripheral
        self.Name = peripheral.identifier()
        self.Rssi = peripheral.rssi()
        self.Address = peripheral.address()

    @property
    def peripheral(self):
        return self._peripheral

    def __lt__(self, other):
        # Sort descending by RSSI then ascending by Name (mirrors C# CompareTo)
        if self.Rssi != other.Rssi:
            return self.Rssi > other.Rssi
        return (self.Name or "") < (other.Name or "")
