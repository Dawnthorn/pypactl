import enum

class SubscriptionMask(enum.IntEnum):
    NULL = 0x0000
    SINK = 0x0001
    SOURCE = 0x0002
    SINK_INPUT = 0x0004
    SOURCE_OUTPUT = 0x0008
    MODULE = 0x0010
    CLIENT = 0x0020
    SAMPLE_CACHE = 0x0040
    SERVER = 0x0080
    AUTOLOAD = 0x0100
    CARD = 0x0200
    ALL = 0x02ff
