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
    from .commands import Component, Attribute, BuildComponent, BuildChannel
    from .commands import BuildAttribute, BuildSpecialCmd, CHNUMSIZE
    from .logger import Logger as _Logger
    from .tcpListener import TcpListener
    from .lock import Locker as _Locker
    from .version import version as _version
except:
    from commands import Component, Attribute, BuildComponent, BuildChannel
    from commands import BuildAttribute, BuildSpecialCmd, CHNUMSIZE
    from logger import Logger as _Logger
    from tcpListener import TcpListener
    from lock import Locker as _Locker
    from version import version as _version
from time import sleep as _sleep
from time import time as _time
from threading import currentThread as _currentThread
from traceback import print_exc


__author__ = "Sergi Blanch-Torné"
__copyright__ = "Copyright 2015, CELLS / ALBA Synchrotron"
__license__ = "GPLv3+"

__all__ = ["scpi"]


# DEPRECATED: flags for service activation
TCPLISTENER_LOCAL = 0b10000000
TCPLISTENER_REMOTE = 0b01000000


def __version__():
    '''Library version with 4 fields: 'a.b.c-d'
       Where the two first 'a' and 'b' comes from the base C library
       (scpi-parser), the third is the build of this cypthon port and the last
       one is a revision number.
    '''
    return _version()


class scpi(_Logger):
    '''This is an object to be build in order to provide to your instrument
       SCPI communications. By now it only provides network (ipv4 and ipv6)
       communications, but if required it can be extended to support other
       types.

       By default it builds sockets that only listen in the loopback network
       interface. By default we like to avoid to expose the conection. There
       are two ways to allow direct remote connections. One in the constructor
       by calling it with the parameter services=TCPLISTENER_REMOTE. The other
       can be called once the object is created by setting the object property
       'remoteAllowed' to True.
    '''
    def __init__(self, commandTree=None, specialCommands=None,
                 local=True, port=5025, autoOpen=False,
                 services=None, writeLock=False, *args, **kwargs):
        super(scpi, self).__init__(*args, **kwargs)
        self._name = "scpi"
        self._commandTree = commandTree or Component()
        self._commandTree.logEnable(self.logState())
        self._commandTree.logLevel(self.logGetLevel())
        self._specialCmds = specialCommands or {}
        self._debug("Special commands: %r" % (specialCommands))
        self._debug("Given commands: %r" % (self._commandTree))
        self._local = local
        self._port = port
        self._services = {}
        if services is not None:
            msg = "The argument 'services' is deprecated, "\
                  "please use the boolean 'local'"
            header = "*"*len(msg)
            if services & (TCPLISTENER_LOCAL | TCPLISTENER_REMOTE):
                self._local = bool(services & TCPLISTENER_LOCAL)
        if autoOpen:
            self.open()
        self.__buildDataFormatAttribute()
        self.__buildSystemComponent(writeLock)

    def __enter__(self):
        self._debug("received a enter() request")
        if not self.isOpen:
            self.open()
        return self

    def __exit__(self, type, value, traceback):
        self._debug("received a exit(%s,%s,%s) request"
                    % (type, value, traceback))
        if self.isOpen:
            self.close()

    def __del__(self):
        self._debug("Delete request received")
        if self.isOpen:
            self.close()

    def __str__(self):
        return "%s" % (self.name)

    def __repr__(self):
        if 'idn' in self._specialCmds:
            return "%s(%s)" % (self.name, self._specialCmds['idn'].read())
        return "%s()" % self.name

    # # communications ares ---

    # TODO: status information method ---
    #       (report the open listeners and accepted connections ongoing).
    # TODO: other incoming channels than network ---

    @property
    def isOpen(self):
        return any([self._services[key].isListening()
                    for key in self._services.keys()])

    def open(self):
        if not self.isOpen:
            self.__buildTcpListener()
        else:
            self._warning("Already Open")

    def close(self):
        if self.isOpen:
            self._debug("Close services")
            for key in self._services.keys():
                self._debug("Close service %s" % key)
                self._services[key].close()
                self._services.pop(key)
            self._debug("Communications finished. Exiting...")
        else:
            self._warning("Already Close")

    def __buildTcpListener(self):
        self._debug("Opening tcp listener (%s)"
                    % ("local" if self._local else "remote"))
        self._services['tcpListener'] = TcpListener(name="TcpListener",
                                                    callback=self.input,
                                                    local=self._local,
                                                    port=self._port,
                                                    debug=self.logState())
        self._services['tcpListener'].listen()

    def addConnectionHook(self, hook):
        for service in self._services.itervalues():
            if hasattr(service, 'addConnectionHook'):
                try:
                    service.addConnectionHook(hook)
                except Exception as e:
                    self._error("Exception setting a hook to %s: %s"
                                % (service, e))
            else:
                self._warning("Service %s doesn't support hooks" % (service))

    def removeConnectionHook(self, hook):
        for service in self._services.itervalues():
            if hasattr(service, 'removeConnectionHook'):
                if not service.removeConnectionHook(hook):
                    self._warning("Service %s refuse to remove the hook"
                                  % (service))
            else:
                self._warning("Service %s doesn't support hooks" % (service))

    def __buildDataFormatAttribute(self):
        self._dataFormat = 'ASCII'
        self.addAttribute('DataFormat', self._commandTree,
                          self.dataFormat, self.dataFormat,
                          allowedArgins=['ASCII', 'QUADRUPLE', 'DOUBLE',
                                         'SINGLE', 'HALF'])

    def __buildSystemComponent(self, writeLock):
        systemTree = self.addComponent('system', self._commandTree)
        self.__buildLockerComponent(systemTree)
        if writeLock:
            self.__buildWLockerComponent(systemTree)
        else:
            self._wlock = None
        # TODO: other SYSTem components from SCPI-99 (pages 21-*)
        #       :SYSTem:PASSword
        #       :SYSTem:PASSword:CDISable
        #       :SYSTem:PASSword:CENAble
        #       :SYSTem:PASSword:NEW
        #       :SYSTem:PRESet
        #       :SYSTem:SECUrity
        #       :SYSTem:SECUrity:IMMEdiate
        #       :SYSTem:SECUrity:STATe
        #       :SYSTem:TIME
        #       :SYSTem:TIME:TIMEr
        #       :SYSTem:TIME:TIMEr:COUNt
        #       :SYSTem:TIME:TIMEr:STATe
        #       :SYSTem:TZONe
        #       :SYSTem:VERSion

    def __buildLockerComponent(self, commandTree):
        self._lock = _Locker(name='readLock', debug=self.logState())
        subTree = self.addComponent('LOCK', commandTree)
        self.addAttribute('owner', subTree, self._lock.Owner, default=True)
        self.addAttribute('release', subTree, readcb=self._lock.release,
                          writecb=self._lock.release)
        self.addAttribute('request', subTree,
                          readcb=self._lock.request,
                          writecb=self._lock.request)

    def __buildWLockerComponent(self, commandTree):
        self._wlock = _Locker(name='writeLock', debug=self.logState())
        subTree = self.addComponent('WLOCK', commandTree)
        self.addAttribute('owner', subTree, self._wlock.Owner, default=True)
        self.addAttribute('release', subTree, readcb=self._wlock.release,
                          writecb=self._wlock.release)
        self.addAttribute('request', subTree,
                          readcb=self._wlock.request,
                          writecb=self._wlock.request)

    @property
    def remoteAllowed(self):
        return not self._services['tcpListener']._local

    @remoteAllowed.setter
    def remoteAllowed(self, value):
        if type(value) is not bool:
            raise AssertionError("Only boolean can be assigned")
        if value != (not self._services['tcpListener']._local):
            tcpListener = self._services.pop('tcpListener')
            tcpListener.close()
            self._debug("Close the active listeners and their connections.")
            while tcpListener.isListening():
                self._warning("Waiting for listerners finish")
                _sleep(1)
            self._debug("Building the new listeners.")
            if value is True:
                self.__buildTcpListener(TCPLISTENER_REMOTE)
            else:
                self.__buildTcpListener(TCPLISTENER_LOCAL)
        else:
            self._debug("Nothing to do when setting like it was.")

    # done communications area ---

    # # command introduction area ---

    def addSpecialCommand(self, name, readcb, writecb=None):
        '''
            Adds a command '*%s'%(name). If finishes with a '?' mark it will
            be called the readcb method, else will be the writecb method.
        '''
        name = name.lower()
        if name.startswith('*'):
            name = name[1:]
        if name.endswith('?'):
            if writecb is not None:
                raise KeyError("Refusing command %s: looks readonly but has "
                               "a query character at the end." % (name))
            name = name[:-1]
        if not name.isalpha():
            raise NameError("Not supported other than alphabetical characters")
        if self._specialCmds is None:
            self._specialCmds = {}
        self._debug("Adding special command '*%s'" % (name))
        BuildSpecialCmd(name, self._specialCmds, readcb, writecb)

    @property
    def specialCommands(self):
        return self._specialCmds.keys()

    def addComponent(self, name, parent):
        if not hasattr(parent, 'keys'):
            raise TypeError("For %s, parent doesn't accept components"
                            % (name))
        if name in parent.keys():
            self._debug("component '%s' already exist" % (name))
            return
        self._debug("Adding component '%s' (%s)" % (name, parent))
        return BuildComponent(name, parent)

    def addChannel(self, name, howMany, parent, startWith=1):
        if not hasattr(parent, 'keys'):
            raise TypeError("For %s, parent doesn't accept components"
                            % (name))
        if name in parent.keys():
            self._debug("component '%s' already exist" % (name))
            return
        self._debug("Adding component '%s' (%s)" % (name, parent))
        return BuildChannel(name, howMany, parent, startWith)

    def addAttribute(self, name, parent, readcb, writecb=None, default=False,
                     allowedArgins=None):
        if not hasattr(parent, 'keys'):
            raise TypeError("For %s, parent doesn't accept attributes"
                            % (name))
        if name in parent.keys():
            self._debug("attribute '%s' already exist" % (name))
            return
        self._debug("Adding attribute '%s' (%s)" % (name, parent))
        return BuildAttribute(name, parent, readcb, writecb, default,
                              allowedArgins)

    def addCommand(self, FullName, readcb, writecb=None, default=False,
                   allowedArgins=None):
        '''
            adds the command in the structure of [X:Y:]Z composed by Components
            X, Y and as many as ':' separated have. The last one will
            correspond with an Attribute with at least a readcb for when it's
            called with a '?' at the end. Or writecb if it's followed by an
            space and something that can be casted after.
        '''
        if FullName.startswith('*'):
            self.addSpecialCommand(FullName, readcb, writecb)
            return
        nameParts = FullName.split(':')
        self._debug("Prepare to add command %s" % (FullName))
        tree = self._commandTree
        # preprocessing:
        for i, part in enumerate(nameParts):
            if len(part) == 0:
                raise NameError("No null names allowed "
                                "(review element %d of %s)" % (i, FullName))
        if len(nameParts) > 1:
            for i, part in enumerate(nameParts[:-1]):
                self.addComponent(part, tree)
                tree = tree[part]
        self.addAttribute(nameParts[-1], tree, readcb, writecb, default,
                          allowedArgins)

    # done command introduction area ---

    # # input/output area ---

    @property
    def commands(self):
        return self._commandTree.keys()

    def dataFormat(self, value=None):
        if value is None:
            return self._dataFormat
        self._dataFormat = value

    def input(self, line):
        self._debug("Received %r input" % (line))
#         if not self._isAccessAllowed():
#             return ''
        start_t = _time()
        while len(line) > 0 and line[-1] in ['\r', '\n', ';']:
            self._debug("from %r remove %r" % (line, line[-1]))
            line = line[:-1]
        if len(line) == 0:
            return ''
        line = line.split(';')
        results = []
        for i, command in enumerate(line):
            command = command.strip()  # avoid '\n' terminator if exist
            self._debug("Processing %dth command: %r" % (i+1, command))
            if command.startswith('*'):
                answer = self._process_special_command(command[1:])
                if answer is not None:
                    results.append(answer)
            elif command.startswith(':'):
                if i == 0:
                    self._error("For command %r: Not possible to start "
                                "with ':', without previous command"
                                % (command))
                    results.append(float('NaN'))
                else:
                    # populate fields pre-':'
                    # with the previous (i-1) command
                    command = "".join("%s%s" % (line[i-1].rsplit(':', 1)[0],
                                                command))
                    self._debug("Command expanded to %r" % (command))
                    answer = self._process_normal_command(command)
                    if answer is not None:
                        results.append(answer)
            else:
                answer = self._process_normal_command(command)
                if answer is not None:
                    results.append(answer)
        self._debug("Answers: %r" % (results))
        answer = ""
        for res in results:
            answer = "".join("%s%s;" % (answer, res))
        self._debug("Answer: %r" % (answer))
        self._debug("Query reply send after %g ms" % ((_time()-start_t)*1000))
        # FIXME: has the last character to be ';'?
        if len(answer[:-1]):
            return answer[:-1]+'\r\n'
        # return answer + '\r\n'
        return ''

    def _process_special_command(self, cmd):
        start_t = _time()
        result = None
        # FIXME: ugly
        self._debug("current special keys: %s" % (self._specialCmds.keys()))
        if cmd.count(':') > 0:  # Not expected in special commands
            return float('NaN')
        for key in self._specialCmds.keys():
            self._debug("testing key %s ?= %s" % (key, cmd))
            if cmd.lower().startswith(key.lower()):
                if cmd.endswith('?'):
                    if self._isAccessAllowed():
                        self._debug("Requesting read of %s" % (key))
                        result = self._specialCmds[key].read()
                        break
                    else:
                        result = float('NaN')
                        break
                if cmd.count(' ') > 0:
                    if self._isAccessAllowed() and\
                            self._isWriteAccessAllowed():
                        bar = cmd.split(' ')
                        name, value = bar
                        self._debug("Requesting write of %s with value %s"
                                    % (name, value))
                        # TODO: By default don't provide a readback,
                        #       but there will be an SCPI command to return
                        #       an answer to the write commands
                        self._specialCmds[name].write(value)
                    break
                self._debug("Requesting write of %s without value" % (key))
                # TODO: By default don't provide a readback,
                #       but there will be an SCPI command to return
                #       an answer to the write commands
                self._specialCmds[key].write()
                break
        self._debug("special command %s processed in %g ms"
                    % (cmd, (_time()-start_t)*1000))
        return result

    def _process_normal_command(self, cmd):
        start_t = _time()
        answer = None
        keywords = cmd.split(':')
        tree = self._commandTree
        channelNum = []
        for key in keywords:
            self._debug("processing %s" % key)
            key, separator, params = self._splitParams(key)
            key = self._check4Channels(key, channelNum)
            try:
                nextNode = tree[key]
                if separator == '?':
                    if self._isAccessAllowed():
                        answer = self._doReadOperation(cmd, tree, key,
                                                       channelNum, params)
                elif separator == ' ' or type(nextNode) == Attribute:
                    # with separator next comes the parameters, without it is
                    # a (write) command without parameters. But in this second
                    # case it must by an Attribute component or it may confuse
                    # with intermediate keys of the command.
                    if self._isAccessAllowed() and \
                            self._isWriteAccessAllowed():
                        self._doWriteOperation(cmd, tree, key, channelNum,
                                               params)
                else:
                    tree = nextNode
            except Exception as e:
                self._error("Not possible to understand key %r (from %r) "
                            "separator %r, params %r" % (key, cmd, separator,
                                                         params))
                if separator == '?':
                    answer = float('NaN')
                print_exc()
                break
        self._debug("command %s processed in %g ms (%r)"
                    % (cmd, (_time()-start_t)*1000, answer))
        return answer

    def _splitParams(self, key):
        for separator, operation in [['?', 'read'], [' ', 'write']]:
            if key.count(separator):
                key, params = key.split(separator)
                if len(params) > 0:
                    self._debug("Found a %s with params: key=%s, params=%s"
                                % (operation, key, params))
                    return key, separator, params
                return key, separator, None
        return key, None, None

    def _check4Channels(self, key, channelNum):
        if key[-CHNUMSIZE:].isdigit():
            channelNum.append(int(key[-CHNUMSIZE:]))
            self._debug("It has been found that this has channels defined "
                        "for keyword %s" % (key))
            key = key[:-CHNUMSIZE]
        return key

    def _doReadOperation(self, cmd, tree, key, channelNum, params):
        try:
            self._debug("Leaf of the tree %r%s"
                        % (key, " (with params=%s)"
                           % params if params else ""))
            if len(channelNum) > 0:
                self._debug("do read with channel")
                if params:
                    answer = tree[key].read(chlst=channelNum,
                                            params=params)
                else:
                    answer = tree[key].read(chlst=channelNum)
            else:
                if params:
                    answer = tree[key].read(params=params)
                else:
                    answer = tree[key].read()
            # With the support for list readings (its conversion
            # to '#NMMMMMMMMM...' stream:
            # TODO: This will require a DataFormat feature to
            #       pack the data in bytes, shorts or longs.
            if answer is None:
                answer = float('NaN')
        except Exception as e:
            self._warning("Exception reading '%s': %s" % (cmd, e))
            answer = float('NaN')
            print_exc()
        return answer

    def _doWriteOperation(self, cmd, tree, key, channelNum, params):
        # TODO: By default don't provide a readback, but there will be an SCPI
        #       command to return an answer to the write commands
        try:
            self._debug("Leaf of the tree %r (%r)" % (key, params))
            if len(channelNum) > 0:
                self._debug("do write (with channel %s) %s: %s"
                            % (channelNum, key, params))
                answer = tree[key].write(chlst=channelNum, value=params)
#                 if answer is None:
#                     answer = tree[key].read(channelNum)
            else:
                self._debug("do write %s: %s" % (key, params))
                answer = tree[key].write(value=params)
#                 if answer is None:
#                     answer = tree[key].read()
        except Exception as e:
            self._warning("Exception writing '%s': %s" % (cmd, e))
            answer = None  # float('NaN')
            print_exc()
        return answer

    # input/output area ---

    # # lock access area ---
    def _BookAccess(self):
        return self._lock.request()

    def _UnbookAccess(self):
        return self._lock.release()

    def _isAccessAllowed(self):
        return self._lock.access()

    def _isAccessBooked(self):
        return self._lock.isLock()

    def _forceAccessRelease(self):
        self._lock._forceRelease()

    def _forceAccessBook(self):
        self._forceAccessRelease()
        return self._BookAccess()

    def _LockOwner(self):
        return self._lock.owner

    def _BookWriteAccess(self):
        if self._wlock:
            return self._wlock.request()
        return False

    def _UnbookWriteAccess(self):
        if self._wlock:
            return self._wlock.release()
        return False

    def _isWriteAccessAllowed(self):
        if self._wlock:
            return self._wlock.access()
        return True

    def _isWriteAccessBooked(self):
        if self._wlock:
            return self._wlock.isLock()
        return False

    def _forceWriteAccessRelease(self):
        if self._wlock:
            self._wlock._forceRelease()

    def _forceWriteAccessBook(self):
        self._forceAccessRelease()
        return self._BookAccess()

    def _WLockOwner(self):
        if self._wlock:
            return self._wlock.owner
        return None
    # lock access area ---
