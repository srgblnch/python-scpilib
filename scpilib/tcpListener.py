# -*- coding: utf-8 -*-
# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

try:
    from .logger import Logger as _Logger
    from .logger import deprecated, deprecated_argument
except Exception:
    from logger import Logger as _Logger
    from logger import deprecated, deprecated_argument
from gc import collect as _gccollect
import socket as _socket
import threading as _threading
from time import sleep as _sleep
from traceback import print_exc as _print_exc

__author__ = "Sergi Blanch-Torné"
__email__ = "sblanch@cells.es"
__copyright__ = "Copyright 2015, CELLS / ALBA Synchrotron"
__license__ = "GPLv3+"


_MAX_CLIENTS = 10


def splitter(data, sep='\r\n'):
    """
    Split the incomming string to separate, in case there are, piled up
    requests. But not confuse with the multiple commands in one request.
    Multiple commands separator is ';', this split is to separate when
    there are '\r' or '\n' or their pairs.

    The separator is trimmed from each request in the returned list.

    If data does not end in either '\r' or '\n', the remaining buffer
    is returned has unprocessed data.

    Examples::

    >>> splitter(b'foo 1\rbar 2\n')
    [b'foo 1', b'bar 2'], b''

    >>> splitter(b'foo 1\rbar 2\nnext...')
    [b'foo 1', b'bar 2'], b'next...'

    :param data: data to separate
    :return: answer: tuple of <list of requests>, <remaining characters>
    """
    data = data.strip(' \t')
    if not data:
        return [], ''
    for c in sep[1:]:
        data = data.replace(c, sep[0])
    result = (line.strip() for line in data.split(sep[0]))
    result = [req for req in result if req]
    has_remaining = data[-1] not in sep
    remaining = result.pop(-1) if has_remaining else b''
    return result, remaining


class TcpListener(_Logger):
    """
        TODO: describe it
    """
    # FIXME: default should be local=False

    _callback = None
    _connection_hooks = None
    _max_clients = None
    _join_event = None

    _local = None
    _port = None

    _host_ipv4 = None
    _listener_ipv4 = None
    _socket_ipv4 = None

    _with_ipv6_support = None
    _host_ipv6 = None
    _listener_ipv6 = None
    _socket_ipv6 = None

    def __init__(self, name=None, callback=None, local=True, port=5025,
                 max_clients=None, ipv6=True,
                 maxClients=None,
                 *args, **kwargs):
        super(TcpListener, self).__init__(*args, **kwargs)
        if maxClients is not None:
            deprecated_argument("TcpListener", "__init__", "maxClients")
            if max_clients is None:
                max_clients = maxClients
        if max_clients is None:
            max_clients = _MAX_CLIENTS
        self._name = name or "TcpListener"
        self._callback = callback
        self._connection_hooks = []
        self._local = local
        self._port = port
        self._max_clients = max_clients
        self._join_event = _threading.Event()
        self._join_event.clear()
        self._connection_threads = {}
        self._with_ipv6_support = ipv6
        self.open()
        self._debug("Listener thread prepared")

    def __enter__(self):
        self._debug("received a enter() request")
        if not self.isOpen:
            self.open()
        return self

    def __exit__(self, type, value, traceback):
        self._debug("received a exit({0},{1},{2}) request",
                    type, value, traceback)
        self.__del__()

    def __del__(self):
        self.close()

    def open(self):
        self.build_ipv4_socket()
        try:
            self.build_ipv6_socket()
        except Exception as exc:
            self._error("IPv6 will not be available due to: {0}", exc)

    def close(self):
        if self._join_event.isSet():
            return
        self._debug("{0} close received", self._name)
        if hasattr(self, '_join_event'):
            self._debug("Deleting TcpListener")
            self._join_event.set()
        self._shutdown_socket(self._socket_ipv4)
        if self._with_ipv6_support and hasattr(self, '_socket_ipv6'):
            self._shutdown_socket(self._socket_ipv6)
        if self._is_listening_ipv4():
            self._socket_ipv4 = None
        if self._with_ipv6_support and self._is_listening_ipv6():
            self._socket_ipv6 = None
        _gccollect()
        while self.is_alive():
            _gccollect()
            self._debug("Waiting for Listener threads")
            _sleep(1)
        self._debug("Everything is close, exiting...")

    @property
    def port(self):
        return self._port

    @property
    def local(self):
        return self._local

    def listen(self):
        self._debug("Launching listener thread")
        self._listener_ipv4.start()
        if hasattr(self, '_listener_ipv6'):
            self._listener_ipv6.start()

    def is_alive(self):
        return self._is_ipv4_listener_alive() or self._is_ipv6_listener_alive()

    @deprecated
    def isAlive(self):
        return self.is_alive()

    def is_listening(self):
        return self._is_listening_ipv4() or self._is_listening_ipv6()

    @deprecated
    def isListening(self):
        return self.is_listening()

    def build_ipv4_socket(self):
        if self._local:
            self._host_ipv4 = '127.0.0.1'
        else:
            self._host_ipv4 = '0.0.0.0'
        self._socket_ipv4 = _socket.socket(
            _socket.AF_INET, _socket.SOCK_STREAM)
        self._socket_ipv4.setsockopt(
            _socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
        self._listener_ipv4 = _threading.Thread(name="Listener4",
                                                target=self.__listener,
                                                args=(self._socket_ipv4,
                                                      self._host_ipv4,))
        self._listener_ipv4.setDaemon(True)

    @deprecated
    def buildIpv4Socket(self):
        return self.build_ipv4_socket()

    def build_ipv6_socket(self):
        if self._with_ipv6_support:
            if not _socket.has_ipv6:
                raise AssertionError("IPv6 not supported by the platform")
            if self._local:
                self._host_ipv6 = '::1'
            else:
                self._host_ipv6 = '::'
            self._socket_ipv6 = _socket.socket(_socket.AF_INET6,
                                               _socket.SOCK_STREAM)
            self._socket_ipv6.setsockopt(_socket.IPPROTO_IPV6,
                                         _socket.IPV6_V6ONLY, True)
            self._socket_ipv6.setsockopt(_socket.SOL_SOCKET,
                                         _socket.SO_REUSEADDR, 1)
            self._listener_ipv6 = _threading.Thread(name="Listener6",
                                                    target=self.__listener,
                                                    args=(self._socket_ipv6,
                                                          self._host_ipv6,))
            self._listener_ipv6.setDaemon(True)

    @deprecated
    def buildIpv6Socket(self):
        return self.build_ipv6_socket()

    @staticmethod
    def _shutdown_socket(sock):
        try:
            sock.shutdown(_socket.SHUT_RDWR)
        except Exception as e:
            _print_exc()

    def _is_ipv4_listener_alive(self):
        return self._listener_ipv4.is_alive()

    def _is_ipv6_listener_alive(self):
        if hasattr(self, '_listener_ipv6'):
            return self._listener_ipv6.is_alive()
        return False

    def __listener(self, scpisocket, scpihost):
        try:
            self.__prepare_listener(scpisocket, scpihost, 5)
            self.__do_listen(scpisocket)
            self._debug("Listener thread finishing")
        except SystemExit as exc:
            self._debug("Received a SystemExit ({0})", exc)
            self.__del__()
        except KeyboardInterrupt as exc:
            self._debug("Received a KeyboardInterrupt ({0})", exc)
            self.__del__()
        except GeneratorExit as exc:
            self._debug("Received a GeneratorExit ({0})", exc)
            self.__del__()

    def __prepare_listener(self, scpisocket, scpihost, maxretries):
        listening = False
        tries = 0
        seconds = 3
        while tries < maxretries:
            try:
                scpisocket.bind((scpihost, self._port))
                scpisocket.listen(self._max_clients)
                self._debug("Listener thread up and running (port {0:d}, with "
                            "a maximum of {1:d} connections in parallel).",
                            self._port, self._max_clients)
                return True
            except Exception as exc:
                tries += 1
                self._error("Couldn't bind the socket. {0}\nException: {1}",
                            "(Retry in {0:d} seconds)".format(seconds)
                            if tries < maxretries else "(No more retries)",
                            exc)
                _sleep(seconds)
        return False

    def __do_listen(self, scpisocket):
        while not self._join_event.isSet():
            try:
                connection, address = scpisocket.accept()
            except Exception as e:
                if self._join_event.isSet():
                    self._debug("Closing Listener")
                    del scpisocket
                    return
                # self._error("Socket Accept Exception: %s" % (e))
                _sleep(3)
            else:
                self.__launch_connection(address, connection)
        scpisocket.close()

    def _is_listening_ipv4(self):
        if hasattr(self, '_socket_ipv4') and \
                hasattr(self._socket_ipv4, 'fileno'):
            return bool(self._socket_ipv4.fileno())
        return False

    def _is_listening_ipv6(self):
        if hasattr(self, '_socket_ipv6') and \
                hasattr(self._socket_ipv6, 'fileno'):
            return bool(self._socket_ipv6.fileno())
        return False

    @property
    def active_connections(self):
        return len(self._connection_threads)

    def __launch_connection(self, address, connection):
        connectionName = "{0}:{1}".format(address[0], address[1])
        try:
            self._debug("Connection request from {0} "
                        "(having {1:d} already active)",
                        connectionName, self.active_connections)
            if connectionName in self._connection_threads and \
                    self._connection_threads[connectionName].is_Alive():
                self.error("New connection from {0} when it has already "
                           "one. refusing the newer.", connectionName)
            elif self.active_connections >= self._max_clients:
                self._error("Reached the maximum number of allowed "
                            "connections ({0:d})", self.active_connections)
            else:
                self._connection_threads[connectionName] = \
                    _threading.Thread(name=connectionName,
                                      target=self.__connection,
                                      args=(address, connection))
                self._debug("Connection for {0} created", connectionName)
                self._connection_threads[connectionName].setDaemon(True)
                self._connection_threads[connectionName].start()
        except Exception as exc:
            self._error("Cannot launch connection request from {0} due to: "
                        "{1}", connectionName, exc)

    def __connection(self, address, connection):
        connectionName = "{0}:{1}".format(address[0], address[1])
        self._debug("Thread for {0} connection", connectionName)
        stream = connection.makefile('rwb', bufsize=0)
        remaining = b''
        while not self._join_event.isSet():
            data = stream.readline()  # data = connection.recv(4096)
            self._info("received from {0}: {1:d} bytes {2!r}",
                       connectionName, len(data), data)
            if len(self._connection_hooks) > 0:
                for hook in self._connection_hooks:
                    try:
                        hook(connectionName, data)
                    except Exception as exc:
                        self._warning("Exception calling {0} hook: {1}",
                                      hook, exc)
            data = remaining + data
            if len(data) == 0:
                self._warning("No data received, termination the connection")
                stream.close()
                connection.close()
                break
            if self._callback is not None:
                lines, remaining = splitter(data)
                for line in lines:
                    ans = self._callback(line)
                    self._debug("scpi.input say {0!r}", ans)
                    stream.write(ans)  # connection.send(ans)
            else:
                remaining = b''
        stream.close()
        self._connection_threads.pop(connectionName)
        self._debug("Ending connection: {0} (having {1} active left)",
                    connectionName, self.active_connections)

    def add_connection_hook(self, hook):
        if callable(hook):
            self._connection_hooks.append(hook)
        else:
            raise TypeError("The hook must be a callable object")

    @deprecated
    def addConnectionHook(self, *args):
        return self.add_connection_hook(*args)

    def remove_connection_hook(self, hook):
        if self._connection_hooks.count(hook):
            self._connection_hooks.pop(self._connection_hooks.index(hook))
            return True
        return False

    @deprecated
    def removeConnectionHook(self, *args):
        return self.remove_connection_hook(*args)
