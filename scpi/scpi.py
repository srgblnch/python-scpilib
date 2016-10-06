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

__author__ = "Sergi Blanch-Torné"
__copyright__ = "Copyright 2015, CELLS / ALBA Synchrotron"
__license__ = "GPLv3+"

__all__ = ["scpi"]


try:
    from .commands import Component, Attribute, BuildComponent, BuildChannel
    from .commands import BuildAttribute, BuildSpecialCmd, AttrTest, ArrayTest
    from .commands import ChannelTest, SubchannelTest, CHNUMSIZE
    from .commands import WattrTest, WchannelTest
    from .logger import Logger as _Logger
    from .tcpListener import TcpListener
    from .version import version as _version
except:
    from commands import Component, Attribute, BuildComponent, BuildChannel
    from commands import BuildAttribute, BuildSpecialCmd, AttrTest, ArrayTest
    from commands import ChannelTest, SubchannelTest, CHNUMSIZE
    from commands import WattrTest, WchannelTest
    from logger import Logger as _Logger
    from tcpListener import TcpListener
    from version import version as _version


from time import sleep as _sleep
from time import time as _time
from threading import currentThread as _currentThread
from traceback import print_exc


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
                 local=True, port=5025, autoOpen=False, debug=False,
                 services=None):
        super(scpi, self).__init__(debug=debug)
        self._name = "scpi"
        self._commandTree = commandTree or Component()
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
            print("%s\n%s\n%s" % (header, msg, header))
            if services & (TCPLISTENER_LOCAL | TCPLISTENER_REMOTE):
                self._local = bool(services & TCPLISTENER_LOCAL)
        if autoOpen:
            self.open()
        self._dataFormat = 'ASCII'
        self.addAttribute('DataFormat', self._commandTree,
                          self.dataFormat, self.dataFormat,
                          allowedArgins=['ASCII', 'QUADRUPLE', 'DOUBLE',
                                         'SINGLE', 'HALF'])

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
                                                    debug=self._debugFlag)
        self._services['tcpListener'].listen()

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
                results.append(self._process_special_command(command[1:]))
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
                    results.append(self._process_normal_command(command))
            else:
                results.append(self._process_normal_command(command))
        self._debug("Answers: %r" % (results))
        answer = ""
        for res in results:
            answer = "".join("%s%s;" % (answer, res))
        self._debug("Answer: %r" % (answer))
        self._debug("Query reply send after %g ms" % ((_time()-start_t)*1000))
        # FIXME: has the last character to be ';'?
        return answer[:-1]+'\r\n'
        # return answer + '\r\n'

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
                    self._debug("Requesting read of %s" % (key))
                    result = self._specialCmds[key].read()
                    break
                if cmd.count(' ') > 0:
                    bar = cmd.split(' ')
                    name, value = bar
                    self._debug("Requesting write of %s with value %s"
                                % (name, value))
                    result = self._specialCmds[name].write(value)
                    break
                self._debug("Requesting write of %s without value"
                            % (key))
                result = self._specialCmds[key].write()
                break
        self._debug("special command %s processed in %g ms"
                    % (cmd, (_time()-start_t)*1000))
        if result is None:
            self._warning("Command (%s) not found..." % (cmd))
            return float('NaN')
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
                    answer = self._doReadOperation(cmd, tree, key, channelNum,
                                                   params)
                elif separator == ' ' or type(nextNode) == Attribute:
                    # with separator next comes the parameters, without it is
                    # a (write) command without parameters. But in this second
                    # case it must by an Attribute component or it may confuse
                    # with intermediate keys of the command.
                    answer = self._doWriteOperation(cmd, tree, key, channelNum,
                                                    params)
                else:
                    tree = nextNode
            except Exception as e:
                self._error("Not possible to understand key %r (from %r) "
                            "separator %r, params %r" % (key, cmd, separator,
                                                         params))
                answer = float('NaN')
                break
        self._debug("command %s processed in %g ms"
                    % (cmd, (_time()-start_t)*1000))
        return answer

    def _splitParams(self, key):
        separators = {'?': 'read', ' ': 'write'}
        for separator in separators.keys():
            if key.count(separator):
                key, params = key.split(separator)
                if len(params) > 0:
                    self._debug("Found a %s with params: key=%s, params=%s"
                                % (separators[separator], key, params))
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
        except Exception as e:
            self._warning("Exception reading '%s': %s" % (cmd, e))
            answer = float('NaN')
            print_exc()
        return answer

    def _doWriteOperation(self, cmd, tree, key, channelNum, params):
        try:
            self._debug("Leaf of the tree %r (%r)" % (key, params))
            if len(channelNum) > 0:
                self._debug("do write (with channel %s) %s: %s"
                            % (channelNum, key, params))
                answer = tree[key].write(chlst=channelNum, value=params)
                if answer is None:
                    answer = tree[key].read(channelNum)
            else:
                self._debug("do write %s: %s" % (key, params))
                # TODO: there's a SCPI command to inhibit the answer
                answer = tree[key].write(value=params)
                if answer is None:
                    answer = tree[key].read()
        except Exception as e:
            self._warning("Exception writing '%s': %s" % (cmd, e))
            answer = float('NaN')
            print_exc()
        return answer

    # input/output area ---


# ---- TEST AREA
try:
    from .logger import printHeader as _printHeader
    from .logger import printFooter as _printFooter
except:
    from logger import printHeader as _printHeader
    from logger import printFooter as _printFooter
    from commands import nChannels, nSubchannels


from random import choice as _randomchoice
from random import randint as _randint
from sys import stdout as _stdout


class InstrumentIdentification(object):
    def __init__(self, manufacturer, instrument, serialNumber,
                 firmwareVersion):
        object.__init__(self)
        self.manufacturer = manufacturer
        self.instrument = instrument
        self.serialNumber = serialNumber
        self.firmwareVersion = firmwareVersion

    @property
    def manufacturer(self):
        return self._manufacturerName

    @manufacturer.setter
    def manufacturer(self, value):
        self._manufacturerName = str(value)

    @property
    def instrument(self):
        return self._instrumentName

    @instrument.setter
    def instrument(self, value):
        self._instrumentName = str(value)

    @property
    def serialNumber(self):
        return self._serialNumber

    @serialNumber.setter
    def serialNumber(self, value):
        self._serialNumber = str(value)

    @property
    def firmwareVersion(self):
        return self._firmwareVersion

    @firmwareVersion.setter
    def firmwareVersion(self, value):
        self._firmwareVersion = str(value)

    def idn(self):
        return "%s,%s,%s,%s" % (self.manufacturer, self.instrument,
                                self.serialNumber, self.firmwareVersion)


stepTime = .1
concatenatedCmds = 50
waitMsg = "wait..."


def _wait(t):
    _stdout.write(waitMsg)
    _stdout.flush()
    _sleep(t)
    _stdout.write("\r"+" "*len(waitMsg)+"\r")
    _stdout.flush()


def _interTestWait():
    _wait(stepTime)


def _afterTestWait():
    _wait(stepTime*10)


def testScpi(debug=False):
    start_t = _time()
    _printHeader("Testing scpi main class (version %s)" % (_version()))
    # ---- BuildSpecial('IDN',specialSet,identity.idn)
    with scpi(local=True, debug=debug) as scpiObj:
        results = []
        resultMsgs = []
        for test in [checkIDN,
                     addInvalidCmds,
                     addValidCommands,
                     checkCommandQueries,
                     checkCommandWrites,
                     checkNonexistingCommands,
                     checkArrayAnswers,
                     checkMultipleCommands,
                     checkReadWithParams,
                     checkWriteWithoutParams
                     ]:
            result, msg = test(scpiObj)
            results.append(result)
            resultMsgs.append(msg)
            _afterTestWait()
    if all(results):
        _printHeader("All tests passed: everything OK (%g s)"
                     % (_time()-start_t))
    else:
        _printHeader("ALERT!! NOT ALL THE TESTS HAS PASSED. Check the list "
                     "(%g s)" % (_time()-start_t))
    for result in resultMsgs:
        print(result)


def checkIDN(scpiObj):
    _printHeader("Test instrument identification")
    try:
        identity = InstrumentIdentification('ALBA', 'test', 0, __version__())
        scpiObj.addSpecialCommand('IDN', identity.idn)
        cmd = "*idn?"
        answer = scpiObj.input(cmd)
        print("\tRequest identification: %s\n\tAnswer: %r" % (cmd, answer))
        result = True, "Identification test PASSED"
    except:
        result = False, "Identification test FAILED"
    _printFooter(result[1])
    return result


def addInvalidCmds(scpiObj):
    _printHeader("Testing to build invalid commands")
    try:
        scpiObj.addCommand(":startswithcolon", readcb=None)
    except NameError as e:
        print("\tNull name test PASSED")
    except Exception as e:
        print("\tUnexpected kind of exception!")
        return False, "Invalid commands test FAILED"
    try:
        scpiObj.addCommand("double::colons", readcb=None)
    except NameError as e:
        print("\tDouble colon name test PASSED")
    except Exception as e:
        print("\tUnexpected kind of exception!")
        return False, "Invalid commands test FAILED"
    try:
        scpiObj.addCommand("nestedSpecial:*special", readcb=None)
    except NameError as e:
        scpiObj._commandTree.pop('nestedSpecial')
        print("\tNested special command test PASSED")
    except Exception as e:
        print("\tUnexpected kind of exception!")
        return False, "Invalid commands test FAILED"
    result = True, "Invalid commands test PASSED"
    _printFooter(result[1])
    return result


def addValidCommands(scpiObj):
    _printHeader("Testing to build valid commands")
    try:
        # ---- valid commands section
        currentObj = AttrTest()
        voltageObj = AttrTest()
        # * commands can de added by telling their full name:
        scpiObj.addCommand('source:current:upper',
                           readcb=currentObj.upperLimit,
                           writecb=currentObj.upperLimit)
        scpiObj.addCommand('source:current:lower',
                           readcb=currentObj.lowerLimit,
                           writecb=currentObj.lowerLimit)
        scpiObj.addCommand('source:current:value',
                           readcb=currentObj.readTest,
                           default=True)
        scpiObj.addCommand('source:voltage:upper',
                           readcb=voltageObj.upperLimit,
                           writecb=voltageObj.upperLimit)
        scpiObj.addCommand('source:voltage:lower',
                           readcb=voltageObj.lowerLimit,
                           writecb=voltageObj.lowerLimit)
        scpiObj.addCommand('source:voltage:value', readcb=voltageObj.readTest,
                           default=True)
        scpiObj.addCommand('source:voltage:exception',
                           readcb=voltageObj.exceptionTest)
        # * They can be also created in an iterative way
        baseCmdName = 'basicloop'
        for (subCmdName, subCmdObj) in [('current', currentObj),
                                        ('voltage', voltageObj)]:
            for (attrName, attrFunc) in [('upper', 'upperLimit'),
                                         ('lower', 'lowerLimit'),
                                         ('value', 'readTest')]:
                if hasattr(subCmdObj, attrFunc):
                    cbFunc = getattr(subCmdObj, attrFunc)
                    if attrName == 'value':
                        default = True
                    else:
                        default = False
                    scpiObj.addCommand('%s:%s:%s'
                                       % (baseCmdName, subCmdName, attrName),
                                       readcb=cbFunc, default=default)
                    # Basically is the same than the first example, but the
                    # addCommand is constructed with variables in neasted loops
        # * Another alternative to create the tree in an iterative way would be
        itCmd = 'iterative'
        itObj = scpiObj.addComponent(itCmd, scpiObj._commandTree)
        for (subcomponent, subCmdObj) in [('current', currentObj),
                                          ('voltage', voltageObj)]:
            subcomponentObj = scpiObj.addComponent(subcomponent, itObj)
            for (attrName, attrFunc) in [('upper', 'upperLimit'),
                                         ('lower', 'lowerLimit'),
                                         ('value', 'readTest')]:
                if hasattr(subCmdObj, attrFunc):
                    cbFunc = getattr(subCmdObj, attrFunc)
                    if attrName == 'value':
                        default = True
                    else:
                        default = False
                    attrObj = scpiObj.addAttribute(attrName, subcomponentObj,
                                                   cbFunc, default=default)
                else:
                    print("%s hasn't %s" % (subcomponentObj, attrFunc))
                    # In this case, the intermediate objects of the tree are
                    # build and it is in the innier loop where they have the
                    # attributes created.
                    #  * Use with very big care this option because the library
                    #  * don't guarantee that all the branches of the tree will
                    #  * have the appropiate leafs.
        # * Example of how can be added a node with channels in the scpi tree
        chCmd = 'channel'
        chObj = scpiObj.addChannel(chCmd, nChannels, scpiObj._commandTree)
        chCurrentObj = ChannelTest(nChannels)
        chVoltageObj = ChannelTest(nChannels)
        for (subcomponent, subCmdObj) in [('current', chCurrentObj),
                                          ('voltage', chVoltageObj)]:
            subcomponentObj = scpiObj.addComponent(subcomponent, chObj)
            for (attrName, attrFunc) in [('upper', 'upperLimit'),
                                         ('lower', 'lowerLimit'),
                                         ('value', 'readTest')]:
                if hasattr(subCmdObj, attrFunc):
                    cbFunc = getattr(subCmdObj, attrFunc)
                    if attrName == 'value':
                        default = True
                    else:
                        default = False
                    attrObj = scpiObj.addAttribute(attrName, subcomponentObj,
                                                   cbFunc, default=default)
        # * Example of how can be nested channel type components in a tree that
        #   already have this channels componets defined.
        measCmd = 'measurements'
        measObj = scpiObj.addComponent(measCmd, chObj)
        fnCmd = 'function'
        fnObj = scpiObj.addChannel(fnCmd, nSubchannels, measObj)
        chfnCurrentObj = SubchannelTest(nChannels, nSubchannels)
        chfnVoltageObj = SubchannelTest(nChannels, nSubchannels)
        for (subcomponent, subCmdObj) in [('current', chfnCurrentObj),
                                          ('voltage', chfnVoltageObj)]:
            subcomponentObj = scpiObj.addComponent(subcomponent, fnObj)
            for (attrName, attrFunc) in [('upper', 'upperLimit'),
                                         ('lower', 'lowerLimit'),
                                         ('value', 'readTest')]:
                if hasattr(subCmdObj, attrFunc):
                    cbFunc = getattr(subCmdObj, attrFunc)
                    if attrName == 'value':
                        default = True
                    else:
                        default = False
                    attrObj = scpiObj.addAttribute(attrName, subcomponentObj,
                                                   cbFunc, default=default)
        print("Command tree build: %r" % (scpiObj._commandTree))
        result = True, "Valid commands test PASSED"
        # TODO: channels with channels until the attributes
    except:
        result = False, "Valid commands test FAILED"
    _printFooter(result[1])
    return result


def checkCommandQueries(scpiObj):
    _printHeader("Testing to command queries")
    try:
        print("Launch tests:")
        cmd = "*IDN?"
        answer = scpiObj.input(cmd)
        print("\tInstrument identification (%s)\n\tAnswer: %s" % (cmd, answer))
        for baseCmd in ['SOURce', 'BASIcloop', 'ITERative']:
            _printHeader("Check %s part of the tree" % (baseCmd))
            doCheckCommands(scpiObj, baseCmd)
        for ch in range(1, nChannels+1):
            baseCmd = "CHANnel%s" % (str(ch).zfill(2))
            _printHeader("Check %s part of the tree" % (baseCmd))
            doCheckCommands(scpiObj, baseCmd)
            fn = _randomchoice(range(1, nSubchannels+1))
            innerCmd = "FUNCtion%s" % (str(fn).zfill(2))
            _printHeader("Check %s + MEAS:%s part of the tree"
                         % (baseCmd, innerCmd))
            doCheckCommands(scpiObj, baseCmd, innerCmd)
        result = True, "Command queries test PASSED"
    except:
        rasult = False, "Command queries test FAILED"
    _printFooter(result[1])
    return result


def checkCommandWrites(scpiObj):
    _printHeader("Testing to command writes")
    try:
        # simple commands ---
        currentConfObj = WattrTest()
        scpiObj.addCommand('source:current:configure',
                           readcb=currentConfObj.readTest,
                           writecb=currentConfObj.writeTest)
        voltageConfObj = WattrTest()
        scpiObj.addCommand('source:voltage:configure',
                           readcb=voltageConfObj.readTest,
                           writecb=voltageConfObj.writeTest)
        for inner in ['current', 'voltage']:
            doWriteCommand(scpiObj, "source:%s:configure" % (inner))
        _wait(1)  # FIXME: remove
        # channel commands ---
        _printHeader("Testing to channel command writes")
        baseCmd = 'writable'
        wObj = scpiObj.addComponent(baseCmd, scpiObj._commandTree)
        chCmd = 'channel'
        chObj = scpiObj.addChannel(chCmd, nChannels, wObj)
        chCurrentObj = WchannelTest(nChannels)
        chVoltageObj = WchannelTest(nChannels)
        for (subcomponent, subCmdObj) in [('current', chCurrentObj),
                                          ('voltage', chVoltageObj)]:
            subcomponentObj = scpiObj.addComponent(subcomponent, chObj)
            for (attrName, attrFunc) in [('upper', 'upperLimit'),
                                         ('lower', 'lowerLimit'),
                                         ('value', 'readTest')]:
                if hasattr(subCmdObj, attrFunc):
                    if attrName == 'value':
                        attrObj = scpiObj.addAttribute(attrName,
                                                       subcomponentObj,
                                                       readcb=subCmdObj.
                                                       readTest,
                                                       writecb=subCmdObj.
                                                       writeTest,
                                                       default=True)
                    else:
                        cbFunc = getattr(subCmdObj, attrFunc)
                        attrObj = scpiObj.addAttribute(attrName,
                                                       subcomponentObj, cbFunc)
        print("\nChecking one write multiple reads\n")
        for i in range(nChannels):
            rndCh = _randint(1, nChannels)
            element = _randomchoice(['current', 'voltage'])
            doWriteChannelCommand(scpiObj, "%s:%s" % (baseCmd, chCmd), rndCh,
                                  element, nChannels)
            _interTestWait()
        print("\nChecking multile writes multiple reads\n")
        for i in range(nChannels):
            testNwrites = _randint(2, nChannels)
            rndChs = []
            while len(rndChs) < testNwrites:
                rndCh = _randint(1, nChannels)
                while rndCh in rndChs:
                    rndCh = _randint(1, nChannels)
                rndChs.append(rndCh)
            element = _randomchoice(['current', 'voltage'])
            values = [_randint(-1000, 1000)]*testNwrites
            doWriteChannelCommand(scpiObj, "%s:%s" % (baseCmd, chCmd), rndChs,
                                  element, nChannels, values)
            _interTestWait()
        print("\nChecking write with allowed values limitation\n")
        selectionCmd = 'source:selection'
        selectionObj = WattrTest()
        selectionObj.writeTest(False)
        scpiObj.addCommand(selectionCmd, readcb=selectionObj.readTest,
                           writecb=selectionObj.writeTest,
                           allowedArgins=[True, False])
        doWriteCommand(scpiObj, selectionCmd, True)
        # doWriteCommand(scpiObj, selectionCmd, 'Fals')
        # doWriteCommand(scpiObj, selectionCmd, 'True')
        try:
            doWriteCommand(scpiObj, selectionCmd, 0)
        except:
            print("\tLimitation values succeed because it raises an exception "
                  "as expected")
        else:
            raise AssertionError("It has been write a value that "
                                 "should not be allowed")
        _interTestWait()
        result = True, "Command queries test PASSED"
    except:
        result = False, "Command queries test FAILED"
    _printFooter(result[1])
    return result


def doWriteCommand(scpiObj, cmd, value=None):
    # first read ---
    answer1 = scpiObj.input("%s?" % cmd)
    print("\tRequested %s initial value: %r" % (cmd, answer1))
    # then write ---
    if value is None:
        value = _randint(-1000, 1000)
        while value == int(answer1.strip()):
            value = _randint(-1000, 1000)
    answer2 = scpiObj.input("%s %s" % (cmd, value))
    print("\tWrite %s value: %s, answer: %r" % (cmd, value, answer2))
    # read again ---
    answer3 = scpiObj.input("%s?" % cmd)
    print("\tRequested %s again value: %r\n" % (cmd, answer3))
    if answer2 != answer3:
        raise AssertionError("Didn't change after write (%s, %s, %s)"
                             % (answer1, answer2, answer3))


def doWriteChannelCommand(scpiObj, pre, inner, post, nCh, value=None):
    maskCmd = "%sNN:%s" % (pre, post)
    # first read all the channels ---
    answer1, toModify, value = _channelCmds_readCheck(scpiObj, pre, inner,
                                                      post, nCh, value)
    print("\tRequested %s initial values:\n\t\t%r\n\t\t(highlight %s)"
          % (maskCmd, answer1, toModify.items()))
    # then write the specified one ---
    answer2, wCmd = _channelCmds_write(scpiObj, pre, inner, post, nCh, value)
    print("\tWrite %s value: %s, answer:\n\t\t%r" % (wCmd, value, answer2))
    # read again all of them ---
    answer3, modified, value = _channelCmds_readCheck(scpiObj, pre, inner,
                                                      post, nCh, value)
    print("\tRequested %s initial values:\n\t\t%r\n\t\t(highlight %s)\n"
          % (maskCmd, answer3, modified.items()))


def _channelCmds_readCheck(scpiObj, pre, inner, post, nCh, value=None):
    rCmd = ''.join("%s%s:%s?;" % (pre, str(ch).zfill(2), post)
                   for ch in range(1, nCh+1))
    answer = scpiObj.input("%s" % rCmd)
    if type(inner) is list:
        toCheck = {}
        for i in inner:
            toCheck[i] = answer.strip().split(';')[i-1]
    else:
        toCheck = {inner: answer.strip().split(';')[inner-1]}
        if value is None:
            value = _randint(-1000, 1000)
            while value == int(toCheck[inner]):
                value = _randint(-1000, 1000)
    return answer, toCheck, value


def _channelCmds_write(scpiObj, pre, inner, post, nCh, value):
    if type(inner) is list:
        if type(value) is not list:
            value = [value]*len(inner)
        while len(value) < len(inner):
            value += value[-1]
        wCmd = ""
        for i, each in enumerate(inner):
            wCmd += "%s%s:%s %s;" % (pre, str(each).zfill(2), post,
                                     value[i])
        wCmd = wCmd[:-1]
    else:
        wCmd = "%s%s:%s %s" % (pre, str(inner).zfill(2), post, value)
    answer = scpiObj.input("%s" % (wCmd))
    return answer, wCmd


def doCheckCommands(scpiObj, baseCmd, innerCmd=None):
    subCmds = ['CURRent', 'VOLTage']
    attrs = ['UPPEr', 'LOWEr', 'VALUe']
    for subCmd in subCmds:
        for attr in attrs:
            if innerCmd:
                cmd = "%s:MEAS:%s:%s:%s?" % (baseCmd, innerCmd, subCmd, attr)
            else:
                cmd = "%s:%s:%s?" % (baseCmd, subCmd, attr)
            answer = scpiObj.input(cmd)
            print("\tRequest %s of %s (%s)\n\tAnswer: %r"
                  % (attr.lower(), subCmd.lower(), cmd, answer))
    _interTestWait()


def checkNonexistingCommands(scpiObj):
    _printHeader("Testing to query commands that doesn't exist")
    try:
        baseCmd = _randomchoice(['SOURce', 'BASIcloop', 'ITERative'])
        subCmd = _randomchoice(['CURRent', 'VOLTage'])
        attr = _randomchoice(['UPPEr', 'LOWEr', 'VALUe'])
        fake = "FAKE"
        # * first level doesn't exist
        start_t = _time()
        cmd = "%s:%s:%s?" % (fake, subCmd, attr)
        answer = scpiObj.input(cmd)
        print("\tRequest non-existing command %s\n\tAnswer: %r (%g ms)"
              % (cmd, answer, (_time()-start_t)*1000))
        # * intermediate level doesn't exist
        cmd = "%s:%s:%s?" % (baseCmd, fake, attr)
        answer = scpiObj.input(cmd)
        print("\tRequest non-existing command %s\n\tAnswer: %r (%g ms)"
              % (cmd, answer, (_time()-start_t)*1000))
        # * Attribute level doesn't exist
        cmd = "%s:%s:%s?" % (baseCmd, subCmd, fake)
        answer = scpiObj.input(cmd)
        print("\tRequest non-existing command %s\n\tAnswer: %r (%g ms)"
              % (cmd, answer, (_time()-start_t)*1000))
        # * Attribute that doesn't respond
        cmd = 'source:voltage:exception'
        answer = scpiObj.input(cmd)
        print("\tRequest existing command but that it raises an exception %s"
              "\n\tAnswer: %r (%g ms)" % (cmd, answer, (_time()-start_t)*1000))
        # * Unexisting Channel
        baseCmd = "CHANnel%s" % (str(nChannels+3).zfill(2))
        cmd = "%s:%s:%s?" % (baseCmd, subCmd, fake)
        answer = scpiObj.input(cmd)
        print("\tRequest non-existing channel %s\n\tAnswer: %r (%g ms)"
              % (cmd, answer, (_time()-start_t)*1000))
        # * Channel below the minimum reference
        cmd = "CHANnel00:VOLTage:UPPEr?"
        answer = scpiObj.input(cmd)
        print("\tRequest non-existing channel %s\n\tAnswer: %r (%g ms)"
              % (cmd, answer, (_time()-start_t)*1000))
        # * Channel above the maximum reference
        cmd = "CHANnel99:VOLTage:UPPEr?"
        answer = scpiObj.input(cmd)
        print("\tRequest non-existing channel %s\n\tAnswer: %r (%g ms)"
              % (cmd, answer, (_time()-start_t)*1000))
        result = True, "Non-existing commands test PASSED"
    except:
        result = False, "Non-existing commands test FAILED"
    _printFooter(result[1])
    return result


def checkArrayAnswers(scpiObj):
    _printHeader("Requesting an attribute the answer of which is an array")
    try:
        baseCmd = 'source'
        attrCmd = 'buffer'
        longTest = ArrayTest(100)
        scpiObj.addCommand(attrCmd, readcb=longTest.readTest)
        # current
        CurrentObj = ArrayTest(5)
        CurrentCmd = "%s:current:%s" % (baseCmd, attrCmd)
        scpiObj.addCommand(CurrentCmd, readcb=CurrentObj.readTest)
        # voltage
        VoltageObj = ArrayTest(5)
        VoltageCmd = "%s:voltage:%s" % (baseCmd, attrCmd)
        scpiObj.addCommand(VoltageCmd, readcb=VoltageObj.readTest)
        # queries
        answersLengths = {}
        for cmd in [attrCmd, CurrentCmd, VoltageCmd]:
            for format in ['ASCII', 'QUADRUPLE', 'DOUBLE', 'SINGLE', 'HALF']:
                scpiObj.input("DataFormat %s" % (format))
                answer = scpiObj.input(cmd + '?')
                print("\tRequest %s \n\tAnswer: %r (len %d)" % (cmd, answer,
                                                                len(answer)))
                if format not in answersLengths:
                    answersLengths[format] = []
                answersLengths[format].append(len(answer))
        print("\n\tanswer lengths summary: %s"
              % "".join('\n\t\t{}:{}'.format(k, v)
                        for k, v in answersLengths.iteritems()))
        result = True, "Array answers test PASSED"
    except:
        result = False, "Array answers test FAILED"
    _printFooter(result[1])
    return result


def checkMultipleCommands(scpiObj):
    _printHeader("Requesting more than one attribute per query")
    try:
        log = []
        for i in range(2, concatenatedCmds+1):
            lst = []
            for j in range(i):
                lst.append(_buildCommand2Test())
            cmds = "".join("%s;" % x for x in lst)[:-1]
            cmdsSplitted = "".join("\t\t%s\n" % cmd for cmd in cmds.split(';'))
            start_t = _time()
            answer = scpiObj.input(cmds)
            nAnswers = len(_cutMultipleAnswer(answer))
            log.append(_time() - start_t)
            print("\tRequest %d attributes in a single query: \n%s\tAnswer: "
                  "%r (%d, %g ms)\n" % (i, cmdsSplitted, answer, nAnswers,
                                        log[-1]*1000))
            if nAnswers != i:
                raise AssertionError("The answer doesn't have the %d expected "
                                     "elements" % (i))
            _interTestWait()
        # TODO: multiple writes
        result = True, "Many commands per query test PASSED"
    except:
        result = False, "Many commands per query test FAILED"
    _printFooter(result[1])
    return result


def checkReadWithParams(scpiObj):
    _printHeader("Attribute read with parameters after the '?'")
    try:
        cmd = 'reader:with:parameters'
        longTest = ArrayTest(100)
        scpiObj.addCommand(cmd, readcb=longTest.readRange)
        scpiObj.input("DataFormat ASCII")
        for i in range(10):
            bar, foo = _randint(0, 100), _randint(0, 100)
            start = min(bar, foo)
            end = max(bar, foo)
            cmdWithParams = "%s?%s,%s" % (cmd, start, end)
            answer = scpiObj.input(cmdWithParams)
            print("\tRequest %s \n\tAnswer: %r (len %d)" % (cmdWithParams,
                                                            answer,
                                                            len(answer)))
        result = True, "Read with parameters test PASSED"
    except:
        result = False, "Read with parameters test FAILED"
    _printFooter(result[1])
    return result


def checkWriteWithoutParams(scpiObj):
    _printHeader("Attribute write without parameters")
    try:
        cmd = 'writter:without:parameters'
        switch = WattrTest()
        scpiObj.addCommand(cmd, readcb=switch.switchTest)
        for i in range(3):
            cmd = "%s%s" % (cmd, " "*i)
            answer = scpiObj.input(cmd)
            print("\tRequest %s \n\tAnswer: %r (len %d)" % (cmd, answer,
                                                            len(answer)))
        result = True, "Write without parameters test PASSED"
    except:
        result = False, "Write without parameters test FAILED"
    _printFooter(result[1])
    return result


def _cutMultipleAnswer(answerStr):
    answerStr = answerStr.strip()
    answersLst = []
    while len(answerStr) != 0:
        if answerStr[0] == '#':
            headerSize = int(answerStr[1])
            bodySize = int(answerStr[2:headerSize+2])
            bodyBlock = answerStr[headerSize+2:bodySize+headerSize+2]
            print("with a headerSize of %d and a bodySize of %s, %d elements "
                  "in the body" % (headerSize, bodySize, len(bodyBlock)))
            answerStr = answerStr[2+headerSize+bodySize:]
            if len(answerStr) > 0:
                answerStr = answerStr[1:]
            answersLst.append(bodyBlock)
        else:
            if answerStr.count(';'):
                one, answerStr = answerStr.split(';', 1)
            else:  # the last element
                one = answerStr
                answerStr = ''
            answersLst.append(one)
    print answersLst
    return answersLst


def _buildCommand2Test():
    baseCmds = ['SOURce', 'BASIcloop', 'ITERative', 'CHANnel']
    subCmds = ['CURRent', 'VOLTage']
    attrs = ['UPPEr', 'LOWEr', 'VALUe']
    baseCmd = _randomchoice(baseCmds)
    if baseCmd in ['CHANnel']:
        baseCmd = "%s%s" % (baseCmd, str(_randint(1, nChannels)).zfill(2))
        if _randint(0, 1):
            baseCmd = "%s:MEAS:FUNC%s" % (baseCmd,
                                          str(_randint(1,
                                                       nSubchannels)).zfill(2))
    subCmd = _randomchoice(subCmds)
    if baseCmd in ['SOURce']:
        attr = _randomchoice(attrs + ['BUFFer'])
    else:
        attr = _randomchoice(attrs)
    return "%s:%s:%s?" % (baseCmd, subCmd, attr)


def main():
    import traceback
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('', "--debug", action="store_true", default=False,
                      help="Set the debug flag")
    (options, args) = parser.parse_args()
    for test in [testScpi]:
        try:
            test(options.debug)
        except Exception as e:
            msg = "Test failed!"
            border = "*"*len(msg)
            msg = "%s\n%s:\n%s" % (border, msg, e)
            print(msg)
            traceback.print_exc()
            print(border)
            return


if __name__ == '__main__':
    main()
