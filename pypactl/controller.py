import asyncio
import logging

from pypactl.async_callback import async_callback
from pypactl.loop import create_connection

class Controller:
    def __init__(self, loop, logger=logging.getLogger('pypactl')):
        self.logger = logger
        self.loop = loop
        self.protocol = None
        self.transport = None


    def close(self):
        if self.transport is None:
            return
        self.transport.close()


    async def server_info(self):
        return await async_callback(self.loop, self.protocol.send_get_server_info)


    async def set_default_sink(self, sink_name):
        return await async_callback(self.loop, self.protocol.send_set_default_sink, sink_name)


    async def sinks(self):
        return await async_callback(self.loop, self.protocol.send_get_sink_info_list)


    async def start(self):
        self.protocol, self.transport = await create_connection(self.loop, logger=self.logger)
        await async_callback(self.loop, self.protocol.add_ready_listener)


    def subscribe(self, callback):
        self.protocol.subscribe(callback)
