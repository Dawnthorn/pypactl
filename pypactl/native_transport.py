import asyncio.selector_events
import logging
import socket

class NativeTransport(asyncio.selector_events._SelectorSocketTransport):
    def __init__(self, loop, sock, protocol, waiter=None, extra=None, server=None, path=None, logger=logging.getLogger('pypactl')):
        self.path = path
        self.logger = logger
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        super().__init__(loop, sock, protocol, waiter, extra, server)


    def _read_ready__data_received(self):
        if self._conn_lost:
            return
        try:
            data, ancillary_data, msg_flags, address = self._sock.recvmsg(self.max_size)
        except (BlockingIOError, InterruptedError):
            return
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as exc:
            self._fatal_error(exc, 'Fatal read error on socket transport')
            return

        if not data:
            self._read_ready__on_eof()
            return

        try:
            self._protocol.msg_received(data, ancillary_data, msg_flags, address)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as exc:
            self._fatal_error(exc, 'Fatal error: protocol.data_received() call failed.')


    def sendmsg(self, data, ancdata=None, flags=0, address=None):
        return self._sock.sendmsg(data, ancdata, flags, address)
