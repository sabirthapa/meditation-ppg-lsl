from enum import IntEnum


class NimCommand(IntEnum):
    FirmwareVersion   = 0
    EnableFlashLog    = 1
    FlashLogWrite     = 2
    IsBusy            = 3
    IsFull            = 4
    EnableFclk        = 5
    DebugFlashLogTest = 6
    DebugBusyError    = 7
