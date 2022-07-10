import asyncio
import logging
import os
import socket

from pypactl.native_protocol import NativeProtocol
from pypactl.native_transport import NativeTransport

logger = logging.getLogger('pypactl')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

async def create_pulse_audio_connection(loop, path, protocol_factory):
    path = os.fspath(path)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, 0)
    try:
        sock.setblocking(False)
        await loop.sock_connect(sock, path)
    except:
        sock.close()
        raise
    waiter = loop.create_future()
    protocol = protocol_factory()
    transport = NativeTransport(loop, sock, protocol, waiter)
    try:
        await waiter
    except:
        transport.close()
        raise
    return protocol, transport


async def client():
    count = 0
    loop = asyncio.get_running_loop()
    on_connection_lost = loop.create_future()
    path = os.path.join('/var/run/user/', str(os.getuid()), 'pulse/native')
    protocol, transport = await create_pulse_audio_connection(loop, path, lambda: NativeProtocol(on_connection_lost))
    try:
        await on_connection_lost
    finally:
        transport.close()


asyncio.run(client())
