from ..devices.accel_id import AccelID


class NrfUseAccel:
    def __init__(self, read_bytes: bytes):
        self.UseAccel    = read_bytes[0] == 1
        self.FreeRunMode = read_bytes[1] == 1
        self.AccelID     = AccelID(read_bytes[2])
