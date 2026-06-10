from enum import IntEnum


class AccelID(IntEnum):
    NONE    = 0
    BMA280  = 1
    KX122   = 2
    LIS2DW12 = 3
    LIS2DS12 = 4
    LIS2DH12 = 5
    LSM6DSRX = 6
    KX132   = 7
