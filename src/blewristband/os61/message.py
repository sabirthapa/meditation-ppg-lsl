from enum import IntEnum


class Message(IntEnum):
    NrfFirmwareVersion             = 0
    NimFirmwareVersion             = 1
    EnableSensors                  = 2
    EnableFlashLog                 = 3
    RegisterValue                  = 4
    NrfConfigVLed                  = 5
    NrfConfigVdd                   = 6
    NrfRtcPrescale                 = 7
    NrfUseAccelerometer            = 8
    NimIsBusy                      = 9
    NimIsFull                      = 10
    NrfConfigVddLdo                = 11
    NrfConfigBbst                  = 12
    NrfBattery                     = 13
    NrfNumPd                       = 14
    NrfConnectionParameters        = 15
    NrfConfigPmic                  = 16
    NimEnableFclk                  = 17
    AlgoAecVersion                 = 18
    AlgoAecEnable                  = 19
    AlgoAecConfig                  = 20
    AlgoAecUpdateAgcTargetPDCurrent = 21
    RegBlockRead                   = 22
    NrfRawFifoMode                 = 23
