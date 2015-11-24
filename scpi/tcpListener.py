###############################################################################
## file :               tcpListener.py
##
## description :        Python module to provide scpi functionality to an 
##                      instrument.
##
## project :            scpi
##
## author(s) :          S.Blanch-Torn\'e
##
## Copyright (C) :      2015
##                      CELLS / ALBA Synchrotron,
##                      08290 Bellaterra,
##                      Spain
##
## This file is part of Tango.
##
## Tango is free software: you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## Tango is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Tango.  If not, see <http:##www.gnu.org/licenses/>.
##
###############################################################################


from logger import Logger as _Logger
import socket as _socket
import threading as _threading


_MAX_CLIENTS = 10


class TcpListener(_Logger):
    """
        TODO: describe it
    """
    #FIXME: default should be local=False
    def __init__(self,name=None,parent=None,local=True,port=5025,
                 maxlisteners=_MAX_CLIENTS,ipv6=True,debug=False):
        #Not in the header of the file due to cross imports
        from scpi import scpi as _scpi
        _Logger.__init__(self,parent,debug)
        if local:
            self._host_ipv4 = '127.0.0.1'#_socket.gethostname()
            self._host_ipv6 = '::1'#_socket.gethostname()
        else:
            self._host = ''
        self._name = name or "TcpListener"
        self._parent = parent
        self._port = port
        self._maxlisteners = maxlisteners
        self._scpi_ipv4 = _socket.socket(_socket.AF_INET,
                                        _socket.SOCK_STREAM)
        if ipv6:
            self._scpi_ipv6 = _socket.socket(_socket.AF_INET6,
                                             _socket.SOCK_STREAM)
        self._joinEvent = _threading.Event()
        self._joinEvent.clear()
        self._listener_ipv4 = _threading.Thread(name="Listener4",
                                                target=self.__listener,
                                                args=(self._scpi_ipv4,
                                                      self._host_ipv4,))
        if ipv6:
            self._listener_ipv6 = _threading.Thread(name="Listener6",
                                                    target=self.__listener,
                                                    args=(self._scpi_ipv6,
                                                          self._host_ipv6,))
        self._connectionThreads = {}
        self._debug("Listener thread prepared")
    
    def __del__(self):
        self.close()

    @property
    def port(self):
        return self._port

    def listen(self):
        self._debug("Launching listener thread")
        self._listener_ipv4.start()
        if hasattr(self,'_scpi_ipv6'):
            self._listener_ipv6.start()

    def close(self):
        self._info("%s close received"%self._name)
        if hasattr(self,'_joinEvent'):
            self._info("Deleting TcpListener")
            self._joinEvent.set()
        self._scpi_ipv4.shutdown(_socket.SHUT_RDWR)
        self._scpi_ipv4.close()
        if hasattr(self,'_scpi_ipv6'):
            self._scpi_ipv6.shutdown(_socket.SHUT_RDWR)
            self._scpi_ipv6.close()

    def __listener(self,scpisocket,scpihost):
        scpisocket.bind((scpihost, self._port))
        scpisocket.listen(self._maxlisteners)
        self._debug("Listener thread up and running")
        while not self._joinEvent.isSet():
            try:
                connection, address = scpisocket.accept()
            except Exception,e:
                if self._joinEvent.isSet():
                    self._info("Closing Listener")
                    return
                self._error("Socket Accept Exception: %s"%e)
            else:
                connectionName = '%s:%s'%(address[0],address[1])
                self._debug('Connection request from %s'%(connectionName))
                if self._connectionThreads.has_key(connectionName) and \
                self._connectionThreads[connectionName].isAlive():
                    self.error("New connection from %s when it has already "\
                               "one. refusing the newer."%(connectionName))
                else:
                    self._connectionThreads[connectionName] = \
                    _threading.Thread(name=connectionName,
                                      target=self.__connection,
                                      args=(address,connection))
                    self._debug("Connection for %s created"%(connectionName))
                    self._connectionThreads[connectionName].start()
        scpisocket.close()
        self._debug("Listener thread finishing")

    def __connection(self,address,connection):
        self._debug("Thread for %s:%s connection"%(address[0],address[1]))
        while not self._joinEvent.isSet():
            data = connection.recv(1024)
            self._debug("received %d bytes"%(len(data)))
            if len(data) == 0:
                self.warning("No data received, termination the connection")
                connection.close()
                return
            if hasattr(self._parent,'input') and \
            callable(getattr(self._parent,"input")):
                ans = self._parent.input(data)
            self._debug("skippy.input say %d"%(res))
            connection.send(ans)
