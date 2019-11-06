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
    from .logger import trace, scpi_debug
    from .logger import timeit, timeit_collection
    from .logger import deprecated, deprecation_collection
    from .tcpListener import TcpListener
    from .lock import Locker as _Locker
    from .version import version as _version
except ValueError:
    from commands import Component, Attribute, BuildComponent, BuildChannel
    from commands import BuildAttribute, BuildSpecialCmd, CHNUMSIZE
    from logger import Logger as _Logger
    from logger import trace, scpi_debug
    from logger import timeit, timeit_collection
    from logger import deprecated, deprecation_collection
    from tcpListener import TcpListener
    from lock import Locker as _Locker
    from version import version as _version
import re
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

PARAM_RE = re.compile('(?P<cmd>[^\s?]+)(?P<query>\?)?(?P<args>.*)?$')


def __version__():
    '''Library version with 4 fields: 'a.b.c-d'
       Where the two first 'a' and 'b' comes from the base C library
       (scpi-parser), the third is the build of this cypthon port and the last
       one is a revision number.
    '''
    return _version()


def split_params(data):
    groups = PARAM_RE.match(data).groupdict()
    args = groups['args'].strip()
    query = '?' if groups['query'] == '?' else (' ' if args else None)
    return groups['cmd'], query, args or None


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

    _name = None
    _command_tree = None

    _data_format = None

    def __init__(self, command_tree=None, specialCommands=None,
                 local=True, port=5025, autoOpen=False,
                 services=None, writeLock=False, debug=False, *args, **kwargs):
        scpi_debug(debug)
        super(scpi, self).__init__(*args, **kwargs)
        self._name = "scpi"
        self._command_tree = command_tree or Component()
        self._command_tree.logEnable(self.logState())
        self._command_tree.logLevel(self.logGetLevel())
        self._specialCmds = specialCommands or {}
        self._debug("Special commands: {0!r}", specialCommands)
        self._debug("Given commands: {0!r}", self._command_tree)
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
        self.__build_data_format_attribute()
        self.__build_system_component(writeLock)

    def __enter__(self):
        self._debug("received a enter() request")
        if not self.isOpen:
            self.open()
        return self

    def __exit__(self, type, value, traceback):
        self._debug("received a exit({0},{1},{2}) request",
                    type, value, traceback)
        if self.isOpen:
            self.close()
        self.__summary_timeit()
        self.__summary_deprecated()

    def __del__(self):
        self._debug("Delete request received")
        if self.isOpen:
            self.close()
        self.__summary_timeit()
        self.__summary_deprecated()

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        if 'idn' in self._specialCmds:
            return "{0}({1})".format(
                self.name, self._specialCmds['idn'].read())
        return "{0}()".format(self.name)

    @property
    def command_tree(self):
        return self._command_tree

    def __summary_timeit(self):
        msg = ""
        aux = {}
        strlen = 0
        for klass in timeit_collection:
            for method in timeit_collection[klass]:
                method_full_name = "{0}.{1}".format(klass, method)
                if len(method_full_name) > strlen:
                    strlen = len(method_full_name)
                value = timeit_collection[klass][method]
                aux[method_full_name] = value
        for name in sorted(aux):
            value = aux[name]
            msg += "\tmethod {1:{0}} {2:4} calls: min {3:06.6f} " \
                   "max {4:06.6f} (mean {5:06.6f} std {6:06.6f})\n" \
                   "".format(strlen, name, len(value), value.min(),
                             value.max(), value.mean(), value.std())
        if len(msg) > 0:
            self._warning("timeit summary:\n{0}", msg)

    def __summary_deprecated(self):
        msg = ""
        aux = {}
        strlen = 0
        for klass in deprecation_collection:
            for method in deprecation_collection[klass]:
                method_full_name = "{0}.{1}".format(klass, method)
                if len(method_full_name) > strlen:
                    strlen = len(method_full_name)
                value = deprecation_collection[klass][method]
                aux[method_full_name] = value
        for name in sorted(aux):
            value = aux[name]
            msg += "\tmethod {1:{0}} {2}\n".format(strlen, name, value)
        if len(msg) > 0:
            self._warning("deprecations summary:\n{0}", msg)

    # # communications ares ---

    # TODO: status information method ---
    #       (report the open listeners and accepted connections ongoing).
    # TODO: other incoming channels than network ---

    @property
    def is_open(self):
        return any([self._services[key].is_listening()
                    for key in self._services.keys()])

    # @deprecated
    @property
    def isOpen(self):
        return self.is_open

    def open(self):
        if not self.isOpen:
            self.__build_tcp_listener()
        else:
            self._warning("Already Open")

    def close(self):
        if self.is_open:
            self._debug("Close services")
            for key in self._services.keys():
                self._debug("Close service {0}", key)
                self._services[key].close()
                self._services.pop(key)
            self._debug("Communications finished. Exiting...")
        else:
            self._warning("Already Close")

    def __build_tcp_listener(self):
        self._debug("Opening tcp listener ({0})",
                    "local" if self._local else "remote")
        self._services['tcpListener'] = TcpListener(name="TcpListener",
                                                    callback=self.input,
                                                    local=self._local,
                                                    port=self._port)
        self._services['tcpListener'].listen()

    def add_connection_hook(self, hook):
        try:
            services = self._services.itervalues()
        except AttributeError:
            services = self._services.values()
        for service in services:
            if hasattr(service, 'addConnectionHook'):
                try:
                    service.addConnectionHook(hook)
                except Exception as e:
                    self._error("Exception setting a hook to {0}: {1}",
                                service, e)
            else:
                self._warning("Service {0} doesn't support hooks", service)

    @deprecated
    def addConnectionHook(self, hook):
        return self.add_connection_hook(hook)

    def remove_connection_hook(self, hook):
        try:
            services = self._services.itervalues()
        except AttributeError:
            services = self._services.values()
        for service in services:
            if hasattr(service, 'removeConnectionHook'):
                if not service.removeConnectionHook(hook):
                    self._warning("Service {0} refuse to remove the hook",
                                  service)
            else:
                self._warning("Service {0} doesn't support hooks", service)

    @deprecated
    def removeConnectionHook(self, hook):
        return self.remove_connection_hook(hook)

    def __build_data_format_attribute(self):
        self._data_format = 'ASCII'
        self.add_attribute('DataFormat', self._command_tree,
                           self.data_format, self.data_format,
                           allowedArgins=['ASCII', 'QUADRUPLE', 'DOUBLE',
                                          'SINGLE', 'HALF'])

    def __build_system_component(self, writeLock):
        system_tree = self.add_component('system', self._command_tree)
        self.__build_locker_component(system_tree)
        if writeLock:
            self.__build_wlocker_component(system_tree)
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

    def __build_locker_component(self, command_tree):
        self._lock = _Locker(name='readLock')
        sub_tree = self.add_component('LOCK', command_tree)
        self.add_attribute('owner', sub_tree, self._lock.Owner, default=True)
        self.add_attribute('release', sub_tree, readcb=self._lock.release,
                           writecb=self._lock.release)
        self.add_attribute('request', sub_tree,
                           readcb=self._lock.request,
                           writecb=self._lock.request)

    def __build_wlocker_component(self, command_tree):
        self._wlock = _Locker(name='writeLock')
        sub_tree = self.add_component('WLOCK', command_tree)
        self.add_attribute('owner', sub_tree, self._wlock.Owner, default=True)
        self.add_attribute('release', sub_tree, readcb=self._wlock.release,
                           writecb=self._wlock.release)
        self.add_attribute('request', sub_tree,
                           readcb=self._wlock.request,
                           writecb=self._wlock.request)

    @property
    def remote_allowed(self):
        return not self._services['tcpListener'].local

    # @deprecated
    @property
    def remoteAllowed(self):
        return self.remote_allowed

    @remote_allowed.setter
    def remote_allowed(self, value):
        if type(value) is not bool:
            raise AssertionError("Only boolean can be assigned")
        if value != (not self._services['tcpListener'].local):
            tcpListener = self._services.pop('tcpListener')
            tcpListener.close()
            self._debug("Close the active listeners and their connections.")
            while tcpListener.is_listening():
                self._warning("Waiting for listerners finish")
                _sleep(1)
            self._debug("Building the new listeners.")
            if value is True:
                self.__build_tcp_listener(TCPLISTENER_REMOTE)
            else:
                self.__build_tcp_listener(TCPLISTENER_LOCAL)
        else:
            self._debug("Nothing to do when setting like it was.")

    # @deprecated
    @remoteAllowed.setter
    def remoteAllowed(self, value):
        self.remote_allowed = value

    # done communications area ---

    # # command introduction area ---

    def add_special_command(self, name, readcb, writecb=None):
        '''
            Adds a command '*%s'%(name). If finishes with a '?' mark it will
            be called the readcb method, else will be the writecb method.
        '''
        name = name.lower()
        if name.startswith('*'):
            name = name[1:]
        if name.endswith('?'):
            if writecb is not None:
                raise KeyError("Refusing command {0}: looks readonly but has "
                               "a query character at the end.".format(name))
            name = name[:-1]
        if not name.isalpha():
            raise NameError("Not supported other than alphabetical characters")
        if self._specialCmds is None:
            self._specialCmds = {}
        self._debug("Adding special command '*{0}'".format(name))
        BuildSpecialCmd(name, self._specialCmds, readcb, writecb)

    @deprecated
    def addSpecialCommand(self, name, readcb, writecb=None):
        return self.add_special_command(name, readcb, writecb)

    @property
    def special_commands(self):
        return self._specialCmds.keys()

    # @deprecated
    @property
    def specialCommands(self):
        return self.special_commands

    def add_component(self, name, parent):
        if not hasattr(parent, 'keys'):
            raise TypeError("For {0}, parent doesn't accept components"
                            "".format(name))
        if name in parent.keys():
            # self._warning("component '%s' already exist" % (name))
            return parent[name]
        self._debug("Adding component '{0}' ({1})", name, parent)
        return BuildComponent(name, parent)

    @deprecated
    def addComponent(self, name, parent):
        return self.add_component(name, parent)

    def add_channel(self, name, howMany, parent, startWith=1):
        if not hasattr(parent, 'keys'):
            raise TypeError("For {0}, parent doesn't accept components"
                            "".format(name))
        if name in parent.keys():
            # self._warning("component '%s' already exist" % (name))
            _howMany = parent[name].howManyChannels
            _startWith = parent[name].firstChannel
            if _howMany != howMany or _startWith != startWith:
                AssertionError("Component already exist but with different "
                               "parameters")
            # once here the user is adding exactly what it's trying to add
            # this is more like a get
            return parent[name]
        self._debug("Adding component '{0}' ({1})", name, parent)
        return BuildChannel(name, howMany, parent, startWith)

    @deprecated
    def addChannel(self, name, howMany, parent, startWith=1):
        return self.add_channel(name, howMany, parent, startWith)

    def add_attribute(self, name, parent, readcb, writecb=None, default=False,
                      allowedArgins=None):
        if not hasattr(parent, 'keys'):
            raise TypeError("For {0}, parent doesn't accept attributes"
                            "".format(name))
        if name in parent.keys():
            self._warning("attribute '{0}' already exist", name)
            _readcb = parent[name].read_cb
            _writecb = parent[name].write_cb
            if _readcb != readcb or _writecb != writecb or \
                    parent.default != name:
                AssertionError("Attribute already exist but with different "
                               "parameters")
            return parent[name]
        self._debug("Adding attribute '{0}' ({1})", name, parent)
        return BuildAttribute(name, parent, readcb, writecb, default,
                              allowedArgins)

    @deprecated
    def addAttribute(self, name, parent, readcb, writecb=None, default=False,
                     allowedArgins=None):
        return self.add_attribute(name, parent, readcb, writecb, default,
                                  allowedArgins)

    def add_command(self, FullName, readcb, writecb=None, default=False,
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
        self._debug("Prepare to add command {0}", FullName)
        tree = self._command_tree
        # preprocessing:
        for i, part in enumerate(nameParts):
            if len(part) == 0:
                raise NameError("No null names allowed "
                                "(review element {0:d} of {1})"
                                "".format(i, FullName))
        if len(nameParts) > 1:
            for i, part in enumerate(nameParts[:-1]):
                self.add_component(part, tree)
                tree = tree[part]
        self.add_attribute(nameParts[-1], tree, readcb, writecb, default,
                           allowedArgins)

    @deprecated
    def addCommand(self, FullName, readcb, writecb=None, default=False,
                   allowedArgins=None):
        self.add_command(FullName, readcb, writecb, default,
                         allowedArgins)

    # done command introduction area ---

    # # input/output area ---

    @property
    def commands(self):
        return self._command_tree.keys()

    def data_format(self, value=None):
        if value is None:
            return self._data_format
        self._data_format = value

    @deprecated
    def dataFormat(self, value=None):
        return self._data_format(value)

    @property
    def valid_separators(self):
        return ['\r', '\n', ';']

    @timeit
    def input(self, line):
        # TODO: Document the 3 answer codes 'ACK', 'NOK' and 'NotAllow'
        #  as well as the float('NaN')
        self._debug("Received {0!r} input", line)
        line = self._prepare_input_line(line)
        results = []
        for i, command in enumerate(line):
            command = command.strip()  # avoid '\n' terminator if exist
            self._debug("Processing {0:d}th command: {1!r}", i+1, command)
            if command.startswith('*'):
                answer = self._process_special_command(command[1:])
                if answer is not None:
                    results.append(answer)
            elif command.startswith(':'):
                command = self._complete_partial_command(command, i, line)
                if command is None:
                    results.append(float('NaN'))
                else:
                    answer = self._process_normal_command(command)
                    if answer is not None:
                        results.append(answer)
            else:
                answer = self._process_normal_command(command)
                if answer is not None:
                    results.append(answer)
        # self._debug("Answers: {0!r}", results)
        answer = ""
        for res in results:
            answer = "".join("{0}{1};".format(answer, res))
        self._debug("Answer: {0}", answer)
        # FIXME: has the last character to be ';'?
        if len(answer[:-1]):
            return answer[:-1]+'\r\n'
        return ''

    @timeit
    def _prepare_input_line(self, input):
        while len(input) > 0 and input[-1] in self.valid_separators:
            self._debug("from {0!r} remove {1!r}", input, input[-1])
            input = input[:-1]
        if len(input) == 0:
            return ''
        return input.split(';')

    @timeit
    def _complete_partial_command(self, command, position, previous):
        if position == 0:
            self._error("For command {0!r}: Not possible to start "
                        "with ':', without previous command",
                        command)
            return
        # populate fields pre-':'
        # with the previous (i-1) command
        command = "".join(
            "{0}{1}".format(previous[position-1].rsplit(':', 1)[0], command))
        self._debug("Command expanded to {0!r}", command)
        return command

    @timeit
    def _process_special_command(self, cmd):
        if not self._is_access_allowed():
            return 'NotAllow'
        if cmd.count(':') > 0:  # Not expected in special commands
            return float('NaN')
        if cmd.endswith('?'):
            is_a_query = True
            cmd = cmd[:-1]
        else:
            if not self._is_write_access_allowed():
                return float('NaN')
            is_a_query = False
            pair = cmd.split(' ', 1)
            if len(pair) == 1:
                cmd, args = pair, None  # write without params
            else:
                cmd, args = pair
        if cmd in self._specialCmds.keys():
            if is_a_query:
                return self._specialCmds[cmd].read()
            return self._specialCmds[cmd].write(args)
        return float('NaN')

    @timeit
    def _process_normal_command(self, cmd):
        if not self._is_access_allowed():
            return 'NotAllow'
        command_words = cmd.split(':')
        subtree = self._command_tree
        channel_stack = None  # if there are more than one channel-like element
        last_word = len(command_words)-1
        for i, word in enumerate(command_words):
            if i != last_word:
                try:
                    if word[-CHNUMSIZE:].isdigit():
                        word, number = word[:-CHNUMSIZE], \
                                       int(word[-CHNUMSIZE:])
                        if channel_stack is None:
                            channel_stack = []
                        channel_stack.append(number)
                except Exception:
                    self._error("Not possible to understand word {0!r} "
                                "(from {1!r})", word, cmd)
                    print_exc()
                    return 'NOK'
            else:
                try:
                    word, separator, params = split_params(word)
                    if separator == '?':
                        return self._do_read_operation(
                            subtree, word, channel_stack, params)
                    else:
                        return self._do_write_operation(
                            subtree, word, channel_stack, params)
                except Exception:
                    self._error("Not possible to understand word {0!r} "
                                "(from {1!r}) separator {2!r}, params {3!r}",
                                word, cmd, separator, params)
                    return 'NOK'
            try:
                subtree = subtree[word]  # __next__()
            except Exception:
                self._error("command {0} not found", word)
                return 'NOK'

    @timeit
    def _do_read_operation(self, subtree, word, channel_stack, params):
        answer = subtree[word].read(chlst=channel_stack, params=params)
        if answer is None:
            answer = float('NaN')
        return answer

    @timeit
    def _do_write_operation(self, subtree, word, channel_stack, params):
        # TODO: By default don't provide a readback, but there will be an SCPI
        #       command to return an answer to the write commands
        if self._is_write_access_allowed():
            answer = subtree[word].write(chlst=channel_stack, value=params)
            if answer is None:
                # FIXME: it must be configurable
                #  if there have to be an answer
                return 'ACK'
            return answer
        else:
            return 'NotAllow'

    # input/output area ---

    # # lock access area ---
    def _book_access(self):
        return self._lock.request()

    @deprecated
    def _BookAccess(self):
        return self._book_access()

    def _unbook_access(self):
        return self._lock.release()

    @deprecated
    def _UnbookAccess(self):
        return self._unbook_access()

    def _is_access_allowed(self):
        return self._lock.access()

    @deprecated
    def _isAccessAllowed(self):
        return self._is_access_allowed()

    def _is_access_booked(self):
        return self._lock.isLock()

    @deprecated
    def _isAccessBooked(self):
        return self._is_access_booked()

    def _force_access_release(self):
        self._lock._forceRelease()

    @deprecated
    def _forceAccessRelease(self):
        return self._force_access_release()

    def _force_access_book(self):
        self._forceAccessRelease()
        return self._BookAccess()

    @deprecated
    def _forceAccessBook(self):
        return self._force_access_book()

    def _lock_owner(self):
        return self._lock.owner

    @deprecated
    def _LockOwner(self):
        return self._lock_owner()

    def _book_write_access(self):
        if self._wlock:
            return self._wlock.request()
        return False

    @deprecated
    def _BookWriteAccess(self):
        return self._book_write_access()

    def __unbook_write_access(self):
        if self._wlock:
            return self._wlock.release()
        return False

    @deprecated
    def _UnbookWriteAccess(self):
        return self.__unbook_write_access()

    def _is_write_access_allowed(self):
        if self._wlock:
            return self._wlock.access()
        return True

    @deprecated
    def _isWriteAccessAllowed(self):
        return self._is_write_access_allowed()

    def _is_write_access_booked(self):
        if self._wlock:
            return self._wlock.isLock()
        return False

    @deprecated
    def _isWriteAccessBooked(self):
        return self._is_write_access_booked()

    def _force_write_access_release(self):
        if self._wlock:
            self._wlock._forceRelease()

    @deprecated
    def _forceWriteAccessRelease(self):
        return self._force_write_access_release()

    def _force_write_access_book(self):
        self._forceAccessRelease()
        return self._BookAccess()

    @deprecated
    def _forceWriteAccessBook(self):
        return self._force_write_access_book()

    def _wlock_owner(self):
        if self._wlock:
            return self._wlock.owner
        return None

    @deprecated
    def _WLockOwner(self):
        return self._wlock_owner()

    # lock access area ---
