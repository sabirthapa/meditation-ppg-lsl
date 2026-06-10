from enum import IntEnum


class NrfCommand(IntEnum):
    FirmwareVersion    = 0
    EnableSensors      = 1
    ConfigVled         = 2
    ConfigVdd          = 3
    RtcPrescale        = 4
    UseAccelerometer   = 5
    ConfigVddLdo       = 6
    ConfigBBst         = 7
    Battery            = 8
    NumPd              = 9
    ConnectionParameters = 10
    ConfigPmic         = 11
    RawFifoMode        = 12
