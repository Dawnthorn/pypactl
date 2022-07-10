import enum

class SubscriptionEventType(enum.IntEnum):
    SINK = 0x0000
    SOURCE = 0x0001
    SINK_INPUT = 0x0002
    SOURCE_OUTPUT = 0x0003
    MODULE = 0x0004
    CLIENT = 0x0005
    SAMPLE_CACHE = 0x0006
    SERVER = 0x0007
    AUTOLOAD = 0x0008
    CARD = 0x0009
    FACILITY_MASK = 0x000F
    NEW = 0x0000
    CHANGE = 0x0010
    REMOVE = 0x0020
    TYPE_MASK = 0x0030
