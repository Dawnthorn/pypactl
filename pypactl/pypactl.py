import argparse
import asyncio
import logging
import aioconsole.stream

from aioconsole import AsynchronousCli
from argparse import ArgumentParser
from pypactl.console import Console
from pypactl.controller import Controller
from pypactl.protocol import Protocol

class Pypactl:
    def __init__(self):
        self.logger = logging.getLogger('pypactl')
        self.logger.addHandler(logging.StreamHandler())
        self.logger.setLevel(logging.ERROR)


    def create_console(self):
        parser = ArgumentParser()
        list_parser = ArgumentParser(description="List information about current PulseAudio state.")
        list_parser.add_argument('type_name', help="sinks")
        set_default_sink_parser = ArgumentParser(description="Set default sink.")
        set_default_sink_parser.add_argument('sink_name', help="Name of the sink to set as default.")
        commands = {
           "list": (self.list, list_parser),
           "info": (self.info, ArgumentParser(description="Server info.")),
           "set-default-sink": (self.set_default_sink, set_default_sink_parser),
           "subscribe": (self.subscribe, ArgumentParser(description="Subcribe to events.")),
        }
        return Console(commands)


    async def info(self, reader, writer):
        self.logger.debug("info")
        server_info = await self.controller.server_info()
        writer.write(f"Server String: {self.controller.transport.path}\n")
        writer.write(f"Library Protocol Version: {Protocol.VERSION}\n")
        writer.write(f"Server Protocol Version: {self.controller.protocol.version}\n")
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
        sinks = await self.controller.sinks()
        for sink in sinks:
            writer.write(f"Sink #{sink.index}\n")
            writer.write(f"\tState: {sink.state}\n")
            writer.write(f"\tName: {sink.name}\n")
            writer.write(f"\tDescription: {sink.description}\n")
            writer.write(f"\tDriver: {sink.driver}\n")
            writer.write(f"\tSample Spec: {sink.sample_spec}\n")
            writer.write(f"\tChannel Map: {sink.channel_map}\n")
            writer.write(f"\tOwner Module: {sink.owner_module}\n")
            writer.write(f"\tMute: {sink.mute}\n")
            writer.write(f"\tVolume: {sink.volume}\n")
            writer.write(f"\tMonitor Source: {sink.monitor_source}\n")
            writer.write(f"\tBase Volume: {sink.base_volume}\n")
            writer.write(f"\tLatency: {sink.latency}\n")
            writer.write(f"\tFlags: {sink.flags}\n")
            writer.write(f"\tProperties:\n")
            for key, value in sink.proplist.items():
                writer.write(f"\t\t{key} = {value}\n")
            writer.write(f"\tPorts:\n")
            for port in sink.ports:
                writer.write(f"\t\t{port}\n")
            writer.write(f"\tActive Port: {sink.active_port.name}\n")
            writer.write(f"\tFormats:\n")
            for format in sink.formats:
                writer.write(f"\t\t{format}\n")


    def on_pulse_audio_event(self, event):
        self.logger.debug(f"on_pulse_audio_event({event})")
        self.writer.write(f"{event.facility.name} {event.type.name}\n")


    async def run(self):
        self.loop = asyncio.get_running_loop()
        self.controller = Controller(self.loop)
        await self.controller.start()
        console = self.create_console()
        prompt = self.loop.create_task(console.interact())
        try:
            await asyncio.ensure_future(prompt)
        except BaseException:
            prompt.cancel()
        finally:
            self.controller.close()


    async def set_default_sink(self, reader, writer, sink_name):
        await self.controller.set_default_sink(sink_name)


    async def subscribe(self, reader, writer):
        self.writer = writer
        self.logger.debug("subscribe")
        self.controller.subscribe(self.on_pulse_audio_event)


def main():
    pypactl = Pypactl()
    asyncio.run(pypactl.run())


if __name__ == "__main__":
    main()
