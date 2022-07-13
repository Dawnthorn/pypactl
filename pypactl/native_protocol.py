import asyncio
import getpass
import locale
import logging
import os
import socket
import struct

from pypactl.command import Command
from pypactl.command_error import CommandError
from pypactl.error_code import ErrorCode
from pypactl.event import Event
from pypactl.packet import Packet
from pypactl.protocol import Protocol
from pypactl.server_info import ServerInfo
from pypactl.sink_info import SinkInfo
from pypactl.sink_port_info import SinkPortInfo
from pypactl.subscription_event_type import SubscriptionEventType
from pypactl.subscription_mask import SubscriptionMask
from pypactl.tag import Tag

class NativeProtocol(asyncio.Protocol):
    FRAME_STRUCT = '!IIIII'

    def __init__(self, on_connection_lost=None, logger = logging.getLogger('pypactl')):
        self.buffer = memoryview(b'')
        self.expecting_frame = True
        self.expected_length = struct.calcsize(self.FRAME_STRUCT)
        self.command_id = 0
        self.on_connection_lost = on_connection_lost
        self.logger = logger
        self.version = Protocol.VERSION
        self.reply_map = {}
        self.subscribers = []
        self.ready_listeners = []


    def add_ready_listener(self, callback):
        self.ready_listeners.append(callback)


    def connection_lost(self, exception):
        if self.on_connection_lost is None:
            return
        self.logger.debug(f"connection_lost({exception})")
        if not self.on_connection_lost.cancelled():
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
        packet.add_id(self.command_id)
        self.command_id += 1
        return packet


    def handle_auth_reply(self, packet):
        self.logger.debug("handle_auth_reply")
        self.version = packet.get_u32()
        self.logger.debug(f"PulseAudio Server Protocol Version: {self.version}")
        self.send_properties()


    def handle_command_error(self, packet):
        self.logger.debug("handle_command_error")
        error_code = ErrorCode(packet.get_u32())
        if not packet.id in self.reply_map:
            self.logger.error(f"Recevied error {packet}, but there's no matching id in the reply_map.")
            return
        method, callback = self.reply_map.pop(packet.id, (None, None))
        raise CommandError(f"There was an error executing command for packet {packet.id}: {error_code.name}.", error_code)


    def handle_command_reply(self, packet):
        if not packet.id in self.reply_map:
            self.logger.error(f"Recevied reply {packet}, but there's no matching id in the reply_map.")
            return
        method, callback = self.reply_map.pop(packet.id, (None, None))
        result = None
        if callable(method):
            result = method(packet)
        if callback is not None:
            callback(result)


    def handle_data(self):
        self.logger.debug(f"handle_data {self.expected_length} {len(self.buffer)} {self.buffer}")
        while len(self.buffer) >= self.expected_length:
            data = self.consume(self.expected_length)
            if self.expecting_frame:
                self.handle_frame(data)
            else:
                self.handle_packet(data)
            self.logger.debug(f"handle_data {self.expected_length} {len(self.buffer)} {self.buffer}")


    def handle_frame(self, data):
        length, channel, offset_hi, offset_lo, flags = struct.unpack(self.FRAME_STRUCT, data)
        self.expecting_frame = False
        self.expected_length = length


    def handle_get_sink_info_list_reply(self, packet):
        self.logger.debug(f"handle_get_sink_info_list_reply")
        self.current_packet_handler = None
        sink_infos = []
        while len(packet.data) > 0:
            sink_info = SinkInfo()
            sink_info.index = packet.get_u32()
            sink_info.name = packet.get_string()
            sink_info.description = packet.get_string()
            sink_info.sample_spec = packet.get_sample_spec()
            sink_info.channel_map = packet.get_channel_map()
            sink_info.owner_module = packet.get_u32()
            sink_info.volume = packet.get_cvolume()
            sink_info.mute = packet.get_boolean()
            sink_info.monitor_source = packet.get_u32()
            sink_info.monitor_source_name = packet.get_string()
            sink_info.latency = packet.get_usec()
            sink_info.driver = packet.get_string()
            sink_info.flags = packet.get_u32()
            if self.version >= 13:
                sink_info.proplist = packet.get_proplist()
                sink_info.configured_latency = packet.get_usec()
            if self.version >= 15:
                sink_info.base_volume = packet.get_volume()
                sink_info.state = packet.get_u32()
                sink_info.n_volume_steps = packet.get_u32()
                sink_info.card = packet.get_u32()
                sink_info.n_ports = packet.get_u32()
            if self.version >= 16:
                sink_info.ports = []
                if sink_info.n_ports > 0:
                    for i in range(0, sink_info.n_ports):
                        sink_port_info = SinkPortInfo()
                        sink_port_info.name = packet.get_string()
                        sink_port_info.description = packet.get_string()
                        sink_port_info.priority = packet.get_u32()
                        sink_port_info.available = packet.get_u32()
                        sink_info.ports.append(sink_port_info)
                    sink_info.ap = packet.get_string()
                    for sink_port_info in sink_info.ports:
                        if sink_port_info.name == sink_info.ap:
                            sink_info.active_port = sink_port_info
            if self.version >= 21:
                n_formats = packet.get_u8()
                sink_info.formats = []
                for i in range(0, n_formats):
                    format_info = packet.get_format_info()
                    sink_info.formats.append(format_info)
            sink_infos.append(sink_info)
        self.logger.debug(f"SinkInfos: {sink_infos}")
        return sink_infos


    def handle_packet(self, data):
        self.expecting_frame = True
        self.expected_length = struct.calcsize(self.FRAME_STRUCT)
        packet = Packet(data)
        packet.parse_command()
        self.logger.debug(f"Packet: {packet}")
        method_name = f"handle_command_{packet.command.name.lower()}"
        method = getattr(self, method_name)
        if callable(method):
            method(packet)
        else:
            self.logger.error(f"Unexpected packet: {packet}")


    def handle_command_subscribe_event(self, packet):
        event = Event()
        event.info = packet.get_u32()
        event.facility = SubscriptionEventType(event.info & SubscriptionEventType.FACILITY_MASK)
        event.type = SubscriptionEventType(event.info & SubscriptionEventType.TYPE_MASK)
        event.index = packet.get_u32()
        self.logger.debug(f"handle_subscribe_event {event.info} {event.type} {event.facility} {event.index}")
        for callback in self.subscribers:
            callback(event)



    def handle_properties_reply(self, packet):
        self.logger.debug("handle_properties_reply")
        command_id = packet.get_u32()
        for callback in self.ready_listeners:
            callback()


    def handle_server_info_reply(self, packet):
        self.logger.debug("handle_server_info_reply")
        server_info = ServerInfo()
        server_info.package_name = packet.get_string()
        server_info.package_version = packet.get_string()
        server_info.user_name = packet.get_string()
        server_info.host_name = packet.get_string()
        server_info.defalt_sample_spec = packet.get_sample_spec()
        server_info.default_sink = packet.get_string()
        server_info.default_source = packet.get_string()
        server_info.cookie = packet.get_u32()
        if self.version >= 15:
            server_info.default_channel_map = packet.get_channel_map()
        self.logger.debug(f"server_info: {server_info}")
        return server_info


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
        self.setup_reply(packet.id, self.handle_auth_reply)


    def send_get_server_info(self, callback=None):
        self.logger.debug("send_server_info")
        packet = self.create_command_packet(Command.GET_SERVER_INFO)
        self.send_packet(packet)
        self.setup_reply(packet.id, self.handle_server_info_reply, callback)


    def send_get_sink_info_list(self, callback = None):
        self.logger.debug(f"send_get_sink_info_list {callback}")
        packet = self.create_command_packet(Command.GET_SINK_INFO_LIST)
        self.send_packet(packet)
        self.setup_reply(packet.id, self.handle_get_sink_info_list_reply, callback)


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
        self.setup_reply(packet.id, self.handle_properties_reply)


    def send_set_default_sink(self, sink_name, callback=None):
        self.logger.debug(f"send_set_default_sink({sink_name}")
        packet = self.create_command_packet(Command.SET_DEFAULT_SINK)
        packet.add_string(sink_name)
        self.send_packet(packet)
        self.setup_reply(packet.id, None, callback)


    def send_subscribe(self, callback=None):
        self.logger.debug("send_subscribe")
        packet = self.create_command_packet(Command.SUBSCRIBE)
        packet.add_u32(SubscriptionMask.ALL)
        self.send_packet(packet)
        self.setup_reply(packet.id, self.handle_subscribe_reply, callback)


    def setup_reply(self, id, method, callback=None):
        self.reply_map[id] = (method, callback)


    def subscribe(self, callback=None):
        if len(self.subscribers) == 0:
            self.send_subscribe()
        self.subscribers.append(callback)


    def unsubscribe(self, callback):
        self.subscribers.remove(callback)
