import argparse
import asyncio
import logging

from aioconsole import AsynchronousCli
from argparse import ArgumentParser
from pypactl.console import Console
from pypactl.native_protocol import NativeProtocol
from pypactl.loop import create_connection
from pypactl.protocol import Protocol

class Pypactl:
    def __init__(self):
        self.logger = logging.getLogger('pypactl')
        self.logger.addHandler(logging.StreamHandler())
        self.logger.setLevel(logging.ERROR)


    def create_console(self, streams=None):
        parser = ArgumentParser()
        list_parser = ArgumentParser(description="List information about current PulseAudio state.")
        list_parser.add_argument('type_name', help="sinks")
        commands = {
           "list": (self.list, list_parser),
           "info": (self.info, ArgumentParser(description="Server info.")),
           "subscribe": (self.subscribe, ArgumentParser(description="Subcribe to events.")),
        }
        return Console(commands)


    async def info(self, reader, writer):
        self.logger.debug("info")
        future = self.loop.create_future()
        self.protocol.send_server_info(future)
        server_info = await future
        writer.write(f"Server String: {self.transport.path}\n")
        writer.write(f"Library Protocol Version: {Protocol.VERSION}\n")
        writer.write(f"Server Protocol Version: {self.protocol.version}\n")
        writer.write(f"Is Local: yes\n")
        writer.write(f"Client Index:\n")
        writer.write(f"Tile Size:\n")
        writer.write(f"User Name: {server_info.user_name}\n")
        writer.write(f"Host Name: {server_info.host_name}\n")
        writer.write(f"Server Name: {server_info.package_name}\n")
        writer.write(f"Server Version: {server_info.package_version}\n")
        writer.write(f"Default Sample Specification: {server_info.default_sample_spec}\n")
        writer.write(f"Default Channel Map: {server_info.default_channel_map}\n")
        writer.write(f"Default Sink: {server_info.default_sink}\n")
        writer.write(f"Default Source: {server_info.default_source}\n")
        writer.write(f"Cookie: {server_info.cookie}\n")


    async def list(self, reader, writer, type_name=None):
        self.logger.debug("list")
        future = self.loop.create_future()
        self.protocol.send_get_sink_info_list(future)
        sink_infos = await future
        for sink_info in sink_infos:
            writer.write(f"Sink #{sink_info.index}\n")
            writer.write(f"\tState: {sink_info.state}\n")
            writer.write(f"\tName: {sink_info.name}\n")
            writer.write(f"\tDescription: {sink_info.description}\n")
            writer.write(f"\tDriver: {sink_info.driver}\n")
            writer.write(f"\tSample Spec: {sink_info.sample_spec}\n")
            writer.write(f"\tChannel Map: {sink_info.channel_map}\n")
            writer.write(f"\tOwner Module: {sink_info.owner_module}\n")
            writer.write(f"\tMute: {sink_info.mute}\n")
            writer.write(f"\tVolume: {sink_info.volume}\n")
            writer.write(f"\tMonitor Source: {sink_info.monitor_source}\n")
            writer.write(f"\tBase Volume: {sink_info.base_volume}\n")
            writer.write(f"\tLatency: {sink_info.latency}\n")
            writer.write(f"\tFlags: {sink_info.flags}\n")
            writer.write(f"\tProperties:\n")
            for key, value in sink_info.proplist.items():
                writer.write(f"\t\t{key} = {value}\n")
            writer.write(f"\tPorts:\n")
            for port in sink_info.ports:
                writer.write(f"\t\t{port}\n")
            writer.write(f"\tActive Port: {sink_info.active_port.name}\n")
            writer.write(f"\tFormats:\n")
            for format in sink_info.formats:
                writer.write(f"\t\t{format}\n")


    async def run(self):
        self.loop = asyncio.get_running_loop()
        connection_lost = self.loop.create_future()
        self.protocol, self.transport = await create_connection(self.loop, protocol_factory=lambda logger=None: NativeProtocol(connection_lost), logger=self.logger)
        console = self.create_console()
        prompt = self.loop.create_task(console.interact())
        try:
            done, pending = await asyncio.wait((connection_lost, prompt))
        finally:
            self.transport.close()


    async def subscribe(self, reader, writer):
        self.logger.debug("subscribe")



if __name__ == "__main__":
    pypactl = Pypactl()
    asyncio.run(pypactl.run())
