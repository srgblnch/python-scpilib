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
except:
    from logger import Logger as _Logger
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


class TcpListener(_Logger):
    """
        TODO: describe it
    """
    # FIXME: default should be local=False
    def __init__(self, name=None, callback=None, local=True, port=5025,
                 maxClients=_MAX_CLIENTS, ipv6=True, debug=False):
        super(TcpListener, self).__init__(debug=debug)
        self._name = name or "TcpListener"
        self._callback = callback
        self._connectionHooks = []
        self._local = local
        self._port = port
        self._maxClients = maxClients
        self._joinEvent = _threading.Event()
        self._joinEvent.clear()
        self._connectionThreads = {}
        self._withipv6suport = ipv6
        self.open()
        self._debug("Listener thread prepared")

    def __enter__(self):
        self._debug("received a enter() request")
        if not self.isOpen:
            self.open()
        return self

    def __exit__(self, type, value, traceback):
        self._debug("received a exit(%s,%s,%s) request"
                    % (type, value, traceback))
        self.__del__()

    def __del__(self):
        self.close()

    def open(self):
        self.buildIpv4Socket()
        try:
            self.buildIpv6Socket()
        except Exception as e:
            self._error("IPv6 will not be available due to: %s" % (e))

    def close(self):
        if self._joinEvent.isSet():
            return
        self._debug("%s close received" % (self._name))
        if hasattr(self, '_joinEvent'):
            self._debug("Deleting TcpListener")
            self._joinEvent.set()
        self._shutdownSocket(self._scpi_ipv4)
        if self._withipv6suport and hasattr(self, '_scpi_ipv6'):
            self._shutdownSocket(self._scpi_ipv6)
        if self._isListeningIpv4():
            self._scpi_ipv4 = None
        if self._withipv6suport and self._isListeningIpv6():
            self._scpi_ipv6 = None
        _gccollect()
        while self.isAlive():
            _gccollect()
            self._debug("Waiting for Listener threads")
            _sleep(1)
        self._debug("Everything is close, exiting...")

    @property
    def port(self):
        return self._port

    def listen(self):
        self._debug("Launching listener thread")
        self._listener_ipv4.start()
        if hasattr(self, '_listener_ipv6'):
            self._listener_ipv6.start()

    def isAlive(self):
        return self._isIPv4ListenerAlive() or self._isIPv6ListenerAlive()

    def isListening(self):
        return self._isListeningIpv4() or self._isListeningIpv6()

    def buildIpv4Socket(self):
        if self._local:
            self._host_ipv4 = '127.0.0.1'
        else:
            self._host_ipv4 = '0.0.0.0'
        self._scpi_ipv4 = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        self._scpi_ipv4.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
        self._listener_ipv4 = _threading.Thread(name="Listener4",
                                                target=self.__listener,
                                                args=(self._scpi_ipv4,
                                                      self._host_ipv4,))
        self._listener_ipv4.setDaemon(True)

    def buildIpv6Socket(self):
        if self._withipv6suport:
            if not _socket.has_ipv6:
                raise AssertionError("IPv6 not supported by the platform")
            if self._local:
                self._host_ipv6 = '::1'
            else:
                self._host_ipv6 = '::'
            self._scpi_ipv6 = _socket.socket(_socket.AF_INET6,
                                             _socket.SOCK_STREAM)
            self._scpi_ipv6.setsockopt(_socket.IPPROTO_IPV6,
                                       _socket.IPV6_V6ONLY, True)
            self._scpi_ipv6.setsockopt(_socket.SOL_SOCKET,
                                       _socket.SO_REUSEADDR, 1)
            self._listener_ipv6 = _threading.Thread(name="Listener6",
                                                    target=self.__listener,
                                                    args=(self._scpi_ipv6,
                                                          self._host_ipv6,))
            self._listener_ipv6.setDaemon(True)

    def _shutdownSocket(self, sock):
        try:
            sock.shutdown(_socket.SHUT_RDWR)
        except Exception as e:
            _print_exc()

    def _isIPv4ListenerAlive(self):
        return self._listener_ipv4.isAlive()

    def _isIPv6ListenerAlive(self):
        if hasattr(self, '_listener_ipv6'):
            return self._listener_ipv6.isAlive()
        return False

    def __listener(self, scpisocket, scpihost):
        try:
            self.__prepareListener(scpisocket, scpihost, 5)
            self.__doListen(scpisocket)
            self._debug("Listener thread finishing")
        except SystemExit as e:
            self._debug("Received a SystemExit (%s)" % (e))
            self.__del__()
        except KeyboardInterrupt as e:
            self._debug("Received a KeyboardInterrupt (%s)" % (e))
            self.__del__()
        except GeneratorExit as e:
            self._debug("Received a GeneratorExit (%s)" % (e))
            self.__del__()

    def __prepareListener(self, scpisocket, scpihost, maxretries):
        listening = False
        tries = 0
        seconds = 3
        while tries < maxretries:
            try:
                scpisocket.bind((scpihost, self._port))
                scpisocket.listen(self._maxClients)
                self._debug("Listener thread up and running (port %d, with "
                            "a maximum of %d connections in parallel)."
                            % (self._port, self._maxClients))
                return True
            except Exception as e:
                tries += 1
                self._error("Couldn't bind the socket. %s\nException: %s"
                            % ("(Retry in %d seconds)" % (seconds)
                               if tries < maxretries else "(No more retries)",
                               e))
                _sleep(seconds)
        return False

    def __doListen(self, scpisocket):
        while not self._joinEvent.isSet():
            try:
                connection, address = scpisocket.accept()
            except Exception as e:
                if self._joinEvent.isSet():
                    self._debug("Closing Listener")
                    del scpisocket
                    return
                self._error("Socket Accept Exception: %s" % (e))
                _sleep(3)
            else:
                self.__launchConnection(address, connection)
        scpisocket.close()

    def _isListeningIpv4(self):
        if hasattr(self, '_scpi_ipv4') and hasattr(self._scpi_ipv4, 'fileno'):
            return bool(self._scpi_ipv4.fileno())
        return False

    def _isListeningIpv6(self):
        if hasattr(self, '_scpi_ipv6') and hasattr(self._scpi_ipv6, 'fileno'):
            return bool(self._scpi_ipv6.fileno())
        return False

    @property
    def nActiveConnections(self):
        return len(self._connectionThreads)

    def __launchConnection(self, address, connection):
        connectionName = '%s:%s' % (address[0], address[1])
        try:
            self._debug('Connection request from %s (having %d already active)'
                        % (connectionName, self.nActiveConnections))
            if connectionName in self._connectionThreads and \
                    self._connectionThreads[connectionName].isAlive():
                self.error("New connection from %s when it has already "
                           "one. refusing the newer." % (connectionName))
            elif self.nActiveConnections >= self._maxClients:
                self._error("Reached the maximum number of allowed "
                            "connections (%d)" % (self.nActiveConnections))
            else:
                self._connectionThreads[connectionName] = \
                    _threading.Thread(name=connectionName,
                                      target=self.__connection,
                                      args=(address, connection))
                self._debug("Connection for %s created" % (connectionName))
                self._connectionThreads[connectionName].setDaemon(True)
                self._connectionThreads[connectionName].start()
        except Exception as e:
            self._error("Cannot launch connection request from %s due to: %s"
                        % (connectionName, e))

    def __connection(self, address, connection):
        connectionName = '%s:%s' % (address[0], address[1])
        self._debug("Thread for %s connection" % (connectionName))
        while not self._joinEvent.isSet():
            data = connection.recv(1024)
            self._info("received from %s: %d bytes %r"
                       % (connectionName, len(data), data))
            if len(self._connectionHooks) > 0:
                for hook in self._connectionHooks:
                    try:
                        hook(connectionName, data)
                    except Exception as e:
                        self._warning("Exception calling %s hook: %s"
                                      % (hook, e))
            if len(data) == 0:
                self._warning("No data received, termination the connection")
                connection.close()
                break
            if self._callback is not None:
                ans = self._callback(data)
                self._debug("scpi.input say %r" % (ans))
                connection.send(ans)
        self._connectionThreads.pop(connectionName)
        self._debug("Ending connection: %s (having %s active left)"
                    % (connectionName, self.nActiveConnections))

    def addConnectionHook(self, hook):
        if callable(hook):
            self._connectionHooks.append(hook)
        else:
            raise TypeError("The hook must be a callable object")

    def removeConnectionHook(self, hook):
        if self._connectionHooks.count(hook):
            self._connectionHooks.pop(self._connectionHooks.index(hook))
            return True
        return False
