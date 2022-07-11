import asyncio
import logging
import os
import socket

from pypactl.native_protocol import NativeProtocol
from pypactl.native_transport import NativeTransport

async def create_connection(loop, path = None, protocol_factory = None, logger = logging.getLogger('pypactl')):
    if path is None:
        path = os.path.join('/var/run/user/', str(os.getuid()), 'pulse/native')
    path = os.fspath(path)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, 0)
    try:
        sock.setblocking(False)
        await loop.sock_connect(sock, path)
    except:
        sock.close()
        raise
    waiter = loop.create_future()
    if protocol_factory is None:
        protocol_factory = lambda logger=None: NativeProtocol(logger=logger)
    protocol = protocol_factory(logger=logger)
    transport = NativeTransport(loop, sock, protocol, waiter, path=path, logger=logger)
    try:
        await waiter
    except:
        transport.close()
        raise
    return protocol, transport
