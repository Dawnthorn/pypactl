import logging
import struct

from pypactl.channel_map import ChannelMap
from pypactl.command import Command
from pypactl.cvolume import Cvolume
from pypactl.format_info import FormatInfo
from pypactl.invalid_packet import InvalidPacket
from pypactl.sample_spec import SampleSpec
from pypactl.tag import Tag

logger = logging.getLogger('pypactl')

class Packet:
    def __init__(self, data = b''):
        self.data = data
        self.command = None
        self.id = None


    def __repr__(self):
#        data = r'\x' + r'\x'.join(f'{b:02x}' for b in self.data)
        data = self.data
        if isinstance(data, memoryview):
            data = self.data.tobytes()
        return f"<PulseAudioPacket data={data} command={self.command} id={self.id}>"


    def add_arbitrary(self, data):
        self.add_tag(Tag.ARBITRARY)
        self.data += struct.pack('!I', len(data))
        self.data += data


    def add_command(self, command):
        self.command = command
        self.add_u32(command)


    def add_id(self, id):
        self.id = id
        self.add_u32(id)


    def add_property(self, key, value):
        self.add_string(key)
        try:
            data = value.encode('UTF-8')
        except AttributeError:
            data = value
        self.add_u32(len(data) + 1)
        self.add_arbitrary(data + b'\00')


    def add_u32(self, value):
        self.add_tag(Tag.U32)
        self.data += struct.pack('!I', value)


    def add_string(self, string):
        self.add_tag(Tag.STRING)
        self.data += string.encode('UTF-8')
        self.data += b'\x00'


    def add_tag(self, tag):
        self.data += struct.pack('!B', tag)


    def consume(self, length):
        result = self.data[:length]
        self.data = self.data[length:]
        return result


    def consume_u8(self):
        return self.consume(1).tobytes()[0]


    def consume_u32(self):
        data = self.consume(4)
        return struct.unpack('!I', data)[0]


    def consume_u64(self):
        data = self.consume(8)
        return struct.unpack('!Q', data)[0]


    def check_tag(self, expected_tag):
        tag = self.get('!B')[0]
        if tag != expected_tag:
            raise InvalidPacket(f"Expected {expected_tag} but got {tag}.")


    def get(self, format):
        data = self.consume(struct.calcsize(format))
        values = struct.unpack(format, data)
        return values


    def get_boolean(self):
        value = self.consume_u8()
        if value == Tag.BOOLEAN_TRUE:
            return True
        elif value == Tag.BOOLEAN_FALSE:
            return False
        else:
            return -1


    def get_arbitrary(self):
        self.check_tag(Tag.ARBITRARY)
        length = self.consume_u32()
        return self.consume(length)


    def get_channel_map(self):
        self.check_tag(Tag.CHANNEL_MAP)
        channel_map = ChannelMap()
        num_channels = self.consume_u8()
        for i in range(0, num_channels):
            channel_map.channels.append(self.consume_u8())
        return channel_map


    def get_cvolume(self):
        self.check_tag(Tag.CVOLUME)
        cvolume = Cvolume()
        num_channels = self.consume_u8()
        for i in range(0, num_channels):
            cvolume.channels.append(self.consume_u32())
        return cvolume


    def get_format_info(self):
        self.check_tag(Tag.FORMAT_INFO)
        format_info = FormatInfo()
        format_info.encoding = self.get_u8()
        format_info.proplist = self.get_proplist()
        return format_info


    def get_proplist(self):
        self.check_tag(Tag.PROPLIST)
        proplist = {}
        while self.data[0] != Tag.STRING_NULL:
            key = self.get_string()
            length = self.get_u32()
            data = self.get_arbitrary().tobytes().decode('UTF-8')
            proplist[key] = data
        self.consume(1)
        return proplist


    def get_sample_spec(self):
        self.check_tag(Tag.SAMPLE_SPEC)
        sample_spec = SampleSpec()
        sample_spec.format = self.consume_u8()
        sample_spec.channels = self.consume_u8()
        sample_spec.rate = self.consume_u32()
        return sample_spec


    def get_string(self):
        self.check_tag(Tag.STRING)
        eos_index = None
        for i in range(0, len(self.data)):
            if self.data[i] == 0:
                eos_index = i
                break
        value = self.consume(eos_index + 1)
        value = value[:-1]
        return value.tobytes().decode('UTF-8')


    def get_u32(self):
        self.check_tag(Tag.U32)
        return self.consume_u32()


    def get_u8(self):
        self.check_tag(Tag.U8)
        return self.consume_u8()


    def get_usec(self):
        self.check_tag(Tag.USEC)
        return self.consume_u64()


    def get_volume(self):
        self.check_tag(Tag.VOLUME)
        return self.consume_u32()


    def parse_command(self):
        self.command = Command(self.get_u32())
        self.id = self.get_u32()
