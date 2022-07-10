import asyncio
import getpass
import locale
import logging
import os
import socket
import struct

from pypactl.command import Command
from pypactl.packet import Packet
from pypactl.protocol import Protocol
from pypactl.sink_info import SinkInfo
from pypactl.sink_port_info import SinkPortInfo
from pypactl.subscription_event_type import SubscriptionEventType
from pypactl.subscription_mask import SubscriptionMask
from pypactl.tag import Tag

class NativeProtocol(asyncio.Protocol):
    AUTH_STRUCT = '!BIBIBIBI'
    FRAME_STRUCT = '!IIIII'

    def __init__(self, on_connection_lost, logger = logging.getLogger('pypactl')):
        self.buffer = memoryview(b'')
        self.expecting_frame = True
        self.expected_length = struct.calcsize(self.FRAME_STRUCT)
        self.command_index = 0
        self.on_connection_lost = on_connection_lost
        self.current_packet_handler = self.handle_auth_reply
        self.logger = logger


    def connection_lost(self, exception):
        self.logger.debug(f"connection_lost({exception})")
        self.on_connection_lost.set_result(True)


    def connection_made(self, transport):
        self.transport = transport
        self.send_auth()


    def consume(self, length):
        result = self.buffer[:length]
        self.buffer = self.buffer[length:]
        return result


    def create_command_packet(self, command):
        packet = Packet()
        packet.add_command(command)
        packet.add_index(self.command_index)
        self.command_index += 1
        return packet


    def handle_data(self):
        self.logger.debug(f"handle_data {self.expected_length} {len(self.buffer)} {self.buffer}")
        while len(self.buffer) >= self.expected_length:
            data = self.consume(self.expected_length)
            if self.expecting_frame:
                self.handle_frame(data)
            else:
                self.handle_packet(data)
            self.logger.debug(f"handle_data {self.expected_length} {len(self.buffer)} {self.buffer}")


    def handle_auth_reply(self, packet):
        self.logger.debug("handle_auth_reply")
        version = packet.get_u32()
        self.logger.debug(f"PulseAudio Server Protocol Version: {version}")
        self.send_properties()


    def handle_frame(self, data):
        length, channel, offset_hi, offset_lo, flags = struct.unpack(self.FRAME_STRUCT, data)
        self.expecting_frame = False
        self.expected_length = length


    def handle_get_sink_info_list_reply(self, packet):
        self.current_packet_handler = None
        sink_infos = []
        while len(packet.data) > 0:
            sink_info = SinkInfo()
            sink_info.index = packet.get_u32()
            sink_info.name = packet.get_string()
            self.logger.debug(f"name: {sink_info.name}")
            self.logger.debug(f"Foo: {packet.data.tobytes()}")
            sink_info.description = packet.get_string()
            self.logger.debug(f"description: {sink_info.description}")
            sink_info.sample_spec = packet.get_sample_spec()
            self.logger.debug(f"sample_spec: {sink_info.sample_spec}")
            sink_info.channel_map = packet.get_channel_map()
            self.logger.debug(f"channel_map {sink_info.channel_map}")
            sink_info.owner_module = packet.get_u32()
            self.logger.debug(f"owner_module {sink_info.owner_module}")
            sink_info.volume = packet.get_cvolume()
            self.logger.debug(f"volue: {sink_info.volume}")
            sink_info.mute = packet.get_boolean()
            sink_info.monitor_source = packet.get_u32()
            sink_info.monitor_source_name = packet.get_string()
            sink_info.latency = packet.get_usec()
            sink_info.driver = packet.get_string()
            sink_info.flags = packet.get_u32()
            sink_info.proplist = packet.get_proplist()
            sink_info.configured_latency = packet.get_usec()
            sink_info.base_volume = packet.get_volume()
            sink_info.state = packet.get_u32()
            sink_info.n_volume_steps = packet.get_u32()
            sink_info.card = packet.get_u32()
            sink_info.n_ports = packet.get_u32()
            sink_info.ports = []
            if sink_info.n_ports > 0:
                for i in range(0, sink_info.n_ports):
                    sink_port_info = SinkPortInfo()
                    sink_port_info.name = packet.get_string()
                    sink_port_info.description = packet.get_string()
                    sink_port_info.priority = packet.get_u32()
                    sink_port_info.available = packet.get_u32()
                sink_info.ap = packet.get_string()
            n_formats = packet.get_u8()
            for i in range(0, n_formats):
                format_info = packet.get_format_info()
            self.logger.debug(sink_info)
            sink_infos.append(sink_info)
        self.logger.debug(f"SinkInfos: {sink_infos}")


    def handle_packet(self, data):
        self.expecting_frame = True
        self.expected_length = struct.calcsize(self.FRAME_STRUCT)
        packet = Packet(data)
        packet.parse_command()
        self.logger.debug(f"Packet: {packet}")
        if packet.command == Command.SUBSCRIBE_EVENT:
            self.handle_subscribe_event(packet)
        else:
            if self.current_packet_handler is None:
                self.logger.error(f"Received {packet}, but not expecting any.")
            else:
                self.current_packet_handler(packet)


    def handle_properties_reply(self, packet):
        self.logger.debug("handle_properties_reply")
        command_index = packet.get_u32()
        self.send_get_sink_info_list()


    def handle_subscribe_event(self, packet):
        event_info = packet.get_u32()
        event_facility = SubscriptionEventType(event_info & SubscriptionEventType.FACILITY_MASK)
        event_type = SubscriptionEventType(event_info & SubscriptionEventType.TYPE_MASK)
        event_index = packet.get_u32()
        self.logger.debug(f"handle_subscribe_event {event_info} {event_type} {event_facility} {event_index}")


    def handle_subscribe_reply(self, packet):
        self.logger.debug("handle_subscribe_reply")
        self.current_packet_handler = None


    def machine_id(self):
        paths_to_try = [
            '/etc/machine-id',
            '/var/lib/dbus/machine-id',
        ]
        for path in paths_to_try:
            if os.path.exists(path):
                with open(path, 'rb') as machine_id_file:
                    machine_id = machine_id_file.read()
                    return machine_id
        return socket.gethostname()


    def msg_received(self, data, ancillary_data, msg_flags, address):
        self.buffer = memoryview(self.buffer.tobytes() + data)
        self.handle_data()


    def send_auth(self):
        self.logger.debug("send_auth")
        cookie_data = None
        with open('/home/peterh/.config/pulse/cookie', 'rb') as cookie_file:
            cookie_data = cookie_file.read()
        packet = self.create_command_packet(Command.AUTH)
        packet.add_u32(Protocol.VERSION)
        packet.add_arbitrary(cookie_data)
        cmsg_data = struct.pack('III', os.getpid(), os.getuid(), os.getgid())
        iov_data = struct.pack(self.FRAME_STRUCT, len(packet.data), 0xffffffff, 0, 0, 0)
        self.transport.sendmsg([iov_data], [(socket.SOL_SOCKET, socket.SCM_CREDENTIALS, cmsg_data)])
        self.transport.write(packet.data)


    def send_get_sink_info_list(self):
        packet = self.create_command_packet(Command.GET_SINK_INFO_LIST)
        self.send_packet(packet)
        self.current_packet_handler = self.handle_get_sink_info_list_reply


    def send_packet(self, packet):
        self.logger.debug(f"send_packet: {packet}")
        frame = struct.pack(self.FRAME_STRUCT, len(packet.data), 0xffffffff, 0, 0, 0)
        self.transport.write(frame)
        self.transport.write(packet.data)


    def send_properties(self):
        self.logger.debug("send_properties")
        packet = self.create_command_packet(Command.SET_CLIENT_NAME)
        packet.add_tag(Tag.PROPLIST)
        packet.add_property('application.process.id', str(os.getpid()))
        packet.add_property('application.process.user', getpass.getuser())
        packet.add_property('application.process.host', socket.gethostname())
        packet.add_property('application.process.binary', 'pypactl')
        packet.add_property('application.name', 'pypactl')
        lang = locale.setlocale(locale.LC_MESSAGES)
        if lang is not None:
            packet.add_property('application.language', lang)
        display = os.environ.get('DISPLAY', None)
        if display is not None:
            packet.add_property('window.x11.display', display)
        packet.add_property('application.process.machine_id', self.machine_id())
        session_id = os.environ.get('XDG_SESSION_ID', None)
        if session_id is not None:
            packet.add_property('application.process.session_id', '232')
        packet.add_tag(Tag.STRING_NULL)
        self.send_packet(packet)
        self.current_packet_handler = self.handle_properties_reply


    def send_subscribe(self):
        self.logger.debug("send_subscribe")
        packet = self.create_command_packet(Command.SUBSCRIBE)
        packet.add_u32(SubscriptionMask.ALL)
        self.send_packet(packet)
        self.current_packet_handler = self.handle_subscribe_reply