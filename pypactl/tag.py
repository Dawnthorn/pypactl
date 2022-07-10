import enum

class Tag(enum.IntEnum):
    INVALID = 0
    STRING = ord('t')
    STRING_NULL = ord('N')
    U32 = ord('L')
    U8 = ord('B')
    U64 = ord('R')
    S64 = ord('r')
    SAMPLE_SPEC = ord('a')
    ARBITRARY = ord('x')
    BOOLEAN_TRUE = ord('1')
    BOOLEAN_FALSE = ord('0')
    BOOLEAN = ord('1')
    TIMEVAL = ord('T')
    USEC = ord('U')
    CHANNEL_MAP = ord('m')
    CVOLUME = ord('v')
    PROPLIST = ord('P')
    VOLUME = ord('V')
    FORMAT_INFO = ord('f')
