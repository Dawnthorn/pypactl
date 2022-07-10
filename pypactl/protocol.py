import enum

class Protocol(enum.IntEnum):
    FLAG_MASK = 0xFFFF0000
    VERSION_MASK = 0xFFFF00000
    FLAG_SHM = 0x80000000
    FLAG_MEMFD = 0x40000000
    VERSION = 33

