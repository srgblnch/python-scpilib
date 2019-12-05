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
__copyright__ = "Copyright 2016, CELLS / ALBA Synchrotron"
__license__ = "GPLv3+"


try:
    from ._objects import AttrTest, ArrayTest
    from ._objects import ChannelTest, SubchannelTest
    from ._objects import nChannels
    from ._objects import nSubchannels
    from ._objects import WattrTest, WchannelTest
except ValueError:
    from _objects import AttrTest, ArrayTest
    from _objects import ChannelTest, SubchannelTest
    from _objects import nChannels
    from _objects import nSubchannels
    from _objects import WattrTest, WchannelTest
try:
    from ._printing import printHeader as _printHeader
    from ._printing import printFooter as _printFooter
    from ._printing import printInfo as _printInfo
except ValueError:
    from _printing import printHeader as _printHeader
    from _printing import printFooter as _printFooter
    from _printing import printInfo as _printInfo
from random import choice as _randomchoice
from random import randint as _randint
from sys import stdout as _stdout
from scpilib import scpi
from scpilib.version import version as _version
from scpilib.logger import _logger_DEBUG, scpi_timeit_collection
import socket as _socket
from telnetlib import Telnet
from time import sleep as _sleep
from time import time as _time
from threading import currentThread as _currentThread
from threading import Event as _Event
from threading import Lock as _Lock
from threading import Thread as _Thread
from traceback import print_exc


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


def _afterTestWait(pause, msg=None, wait_time=None):
    if pause:
        if msg is None:
            msg = "Press enter to continue... (Ctrl+c to break)"
        try:
            raw_input(msg)  # py2
        except NameError:
            try:
                input(msg)  # py3
            except KeyboardInterrupt:
                return False
        except KeyboardInterrupt:
            return False
    else:
        if wait_time is None:
            wait_time = stepTime*10
        if wait_time > 0:
            _wait(wait_time)
    return True


def testScpi(debug, pause, no_remove):
    start_t = _time()
    _printHeader("Testing scpi main class (version %s)" % (_version()))
    # ---- BuildSpecial('IDN',specialSet,identity.idn)
    with scpi(local=True, debug=debug, writeLock=True) as scpiObj:
        results = []
        resultMsgs = []
        try:
            for test in [
                checkIDN,
                addInvalidCmds,
                addValidCommands,
                checkCommandQueries,
                checkCommandWrites,
                checkNonexistingCommands,
                checkArrayAnswers,
                checkMultipleCommands,
                checkReadWithParams,
                checkWriteWithoutParams,
                # checkLocks,
                # checkTelnetHooks,
            ]:
                result, msg = test(scpiObj)
                results.append(result)
                tag, value = msg.rsplit(' ', 1)
                resultMsgs.append([tag, value])
                if _afterTestWait(pause) is False:
                    break
        except KeyboardInterrupt:
            print("Test interrupted...")
        txt = "Tests completed (Ctrl+c to print the summary and end)"
        _afterTestWait(no_remove, msg=txt, wait_time=0)
    if all(results):
        _printHeader("All tests passed: everything OK (%g s)"
                     % (_time()-start_t))
    else:
        _printHeader("ALERT!! NOT ALL THE TESTS HAS PASSED. Check the list "
                     "(%g s)" % (_time()-start_t))
    length = 0
    for pair in resultMsgs:
        if len(pair[0]) > length:
            length = len(pair[0])
    for result in resultMsgs:
        print("%s%s\t%s%s" % (result[0], " "*(length-len(result[0])),
                              result[1],
                              " *" if result[1] == 'FAILED' else ""))
    print("")


# First descendant level for tests ---


def checkIDN(scpiObj):
    _printHeader("Test instrument identification")
    try:
        identity = InstrumentIdentification('ALBA', 'test', 0, _version())
        scpiObj.add_special_command('IDN', identity.idn)
        cmd = "*idn?"
        answer = _send2Input(scpiObj, cmd)
        print("\tRequest identification: %s\n\tAnswer: %r" % (cmd, answer))
        result = True, "Identification test PASSED"
    except Exception as e:
        print("\tUnexpected kind of exception! %s" % e)
        print_exc()
        result = False, "Identification test FAILED"
    _printFooter(result[1])
    return result


def addInvalidCmds(scpiObj):
    _printHeader("Testing to build invalid commands")
    try:
        scpiObj.add_command(":startswithcolon", readcb=None)
    except NameError as e:
        print("\tNull name test PASSED")
    except Exception as e:
        print("\tUnexpected kind of exception! %s" % e)
        print_exc()
        return False, "Invalid commands test FAILED"
    try:
        scpiObj.add_command("double::colons", readcb=None)
    except NameError as e:
        print("\tDouble colon name test PASSED")
    except Exception as e:
        print("\tUnexpected kind of exception! %s" % e)
        print_exc()
        return False, "Invalid commands test FAILED"
    try:
        scpiObj.add_command("nestedSpecial:*special", readcb=None)
    except NameError as e:
        scpiObj.command_tree.pop('nestedSpecial')
        print("\tNested special command test PASSED")
    except Exception as e:
        print("\tUnexpected kind of exception! %s" % e)
        print_exc()
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
        scpiObj.add_command('source:current:upper',
                            readcb=currentObj.upperLimit,
                            writecb=currentObj.upperLimit)
        scpiObj.add_command('source:current:lower',
                            readcb=currentObj.lowerLimit,
                            writecb=currentObj.lowerLimit)
        scpiObj.add_command('source:current:value',
                            readcb=currentObj.readTest,
                            default=True)
        scpiObj.add_command('source:voltage:upper',
                            readcb=voltageObj.upperLimit,
                            writecb=voltageObj.upperLimit)
        scpiObj.add_command('source:voltage:lower',
                            readcb=voltageObj.lowerLimit,
                            writecb=voltageObj.lowerLimit)
        scpiObj.add_command('source:voltage:value', readcb=voltageObj.readTest,
                            default=True)
        scpiObj.add_command('source:voltage:exception',
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
                    scpiObj.add_command('%s:%s:%s'
                                        % (baseCmdName, subCmdName, attrName),
                                        readcb=cbFunc, default=default)
                    # Basically is the same than the first example,
                    # but the add_command is constructed with variables
                    # in neasted loops
        # * Another alternative to create the tree in an iterative way would be
        itCmd = 'iterative'
        itObj = scpiObj.add_component(itCmd, scpiObj.command_tree)
        for (subcomponent, subCmdObj) in [('current', currentObj),
                                          ('voltage', voltageObj)]:
            subcomponentObj = scpiObj.add_component(subcomponent, itObj)
            for (attrName, attrFunc) in [('upper', 'upperLimit'),
                                         ('lower', 'lowerLimit'),
                                         ('value', 'readTest')]:
                if hasattr(subCmdObj, attrFunc):
                    cbFunc = getattr(subCmdObj, attrFunc)
                    if attrName == 'value':
                        default = True
                    else:
                        default = False
                    attrObj = scpiObj.add_attribute(attrName, subcomponentObj,
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
        chObj = scpiObj.add_channel(chCmd, nChannels, scpiObj.command_tree)
        chCurrentObj = ChannelTest(nChannels)
        chVoltageObj = ChannelTest(nChannels)
        for (subcomponent, subCmdObj) in [('current', chCurrentObj),
                                          ('voltage', chVoltageObj)]:
            subcomponentObj = scpiObj.add_component(subcomponent, chObj)
            for (attrName, attrFunc) in [('upper', 'upperLimit'),
                                         ('lower', 'lowerLimit'),
                                         ('value', 'readTest')]:
                if hasattr(subCmdObj, attrFunc):
                    cbFunc = getattr(subCmdObj, attrFunc)
                    if attrName == 'value':
                        default = True
                    else:
                        default = False
                    attrObj = scpiObj.add_attribute(attrName, subcomponentObj,
                                                    cbFunc, default=default)
        # * Example of how can be nested channel type components in a tree that
        #   already have this channels componets defined.
        measCmd = 'measurements'
        measObj = scpiObj.add_component(measCmd, chObj)
        fnCmd = 'function'
        fnObj = scpiObj.add_channel(fnCmd, nSubchannels, measObj)
        chfnCurrentObj = SubchannelTest(nChannels, nSubchannels)
        chfnVoltageObj = SubchannelTest(nChannels, nSubchannels)
        for (subcomponent, subCmdObj) in [('current', chfnCurrentObj),
                                          ('voltage', chfnVoltageObj)]:
            subcomponentObj = scpiObj.add_component(subcomponent, fnObj)
            for (attrName, attrFunc) in [('upper', 'upperLimit'),
                                         ('lower', 'lowerLimit'),
                                         ('value', 'readTest')]:
                if hasattr(subCmdObj, attrFunc):
                    cbFunc = getattr(subCmdObj, attrFunc)
                    if attrName == 'value':
                        default = True
                    else:
                        default = False
                    attrObj = scpiObj.add_attribute(attrName, subcomponentObj,
                                                    cbFunc, default=default)
        print("Command tree build: %r" % (scpiObj.command_tree))
        result = True, "Valid commands test PASSED"
        # TODO: channels with channels until the attributes
    except Exception as e:
        print("\tUnexpected kind of exception! %s" % e)
        print_exc()
        result = False, "Valid commands test FAILED"
    _printFooter(result[1])
    return result


def checkCommandQueries(scpiObj):
    _printHeader("Testing to command queries")
    try:
        print("Launch tests:")
        cmd = "*IDN?"
        answer = _send2Input(scpiObj, cmd)
        print("\tInstrument identification (%s)\n\tAnswer: %s" % (cmd, answer))
        for baseCmd in ['SOURce', 'BASIcloop', 'ITERative']:
            _printHeader("Check %s part of the tree" % (baseCmd))
            _doCheckCommands(scpiObj, baseCmd)
        for ch in range(1, nChannels+1):
            baseCmd = "CHANnel%s" % (str(ch).zfill(2))
            _printHeader("Check %s part of the tree" % (baseCmd))
            _doCheckCommands(scpiObj, baseCmd)
            fn = _randomchoice(range(1, nSubchannels+1))
            innerCmd = "FUNCtion%s" % (str(fn).zfill(2))
            _printHeader("Check %s + MEAS:%s part of the tree"
                         % (baseCmd, innerCmd))
            _doCheckCommands(scpiObj, baseCmd, innerCmd)
        result = True, "Command queries test PASSED"
    except Exception as e:
        print("\tUnexpected kind of exception! %s" % e)
        print_exc()
        result = False, "Command queries test FAILED"
    _printFooter(result[1])
    return result


def checkCommandWrites(scpiObj):
    _printHeader("Testing to command writes")
    try:
        # simple commands ---
        currentConfObj = WattrTest()
        scpiObj.add_command('source:current:configure',
                            readcb=currentConfObj.readTest,
                            writecb=currentConfObj.writeTest)
        voltageConfObj = WattrTest()
        scpiObj.add_command('source:voltage:configure',
                            readcb=voltageConfObj.readTest,
                            writecb=voltageConfObj.writeTest)
        for inner in ['current', 'voltage']:
            _doWriteCommand(scpiObj, "source:%s:configure" % (inner))
        _wait(1)  # FIXME: remove
        # channel commands ---
        _printHeader("Testing to channel command writes")
        baseCmd = 'writable'
        wObj = scpiObj.add_component(baseCmd, scpiObj.command_tree)
        chCmd = 'channel'
        chObj = scpiObj.add_channel(chCmd, nChannels, wObj)
        chCurrentObj = WchannelTest(nChannels)
        chVoltageObj = WchannelTest(nChannels)
        for (subcomponent, subCmdObj) in [('current', chCurrentObj),
                                          ('voltage', chVoltageObj)]:
            subcomponentObj = scpiObj.add_component(subcomponent, chObj)
            for (attrName, attrFunc) in [('upper', 'upperLimit'),
                                         ('lower', 'lowerLimit'),
                                         ('value', 'readTest')]:
                if hasattr(subCmdObj, attrFunc):
                    if attrName == 'value':
                        attrObj = scpiObj.add_attribute(attrName,
                                                        subcomponentObj,
                                                        readcb=subCmdObj.
                                                        readTest,
                                                        writecb=subCmdObj.
                                                        writeTest,
                                                        default=True)
                    else:
                        cbFunc = getattr(subCmdObj, attrFunc)
                        attrObj = scpiObj.add_attribute(
                            attrName, subcomponentObj, cbFunc)
        print("\nChecking one write multiple reads\n")
        for i in range(nChannels):
            rndCh = _randint(1, nChannels)
            element = _randomchoice(['current', 'voltage'])
            _doWriteChannelCommand(scpiObj, "%s:%s" % (baseCmd, chCmd), rndCh,
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
            _doWriteChannelCommand(scpiObj, "%s:%s" % (baseCmd, chCmd), rndChs,
                                   element, nChannels, values)
            _interTestWait()
        print("\nChecking write with allowed values limitation\n")
        selectionCmd = 'source:selection'
        selectionObj = WattrTest()
        selectionObj.writeTest(False)
        scpiObj.add_command(selectionCmd, readcb=selectionObj.readTest,
                            writecb=selectionObj.writeTest,
                            allowedArgins=[True, False])
        _doWriteCommand(scpiObj, selectionCmd, True)
        # _doWriteCommand(scpiObj, selectionCmd, 'Fals')
        # _doWriteCommand(scpiObj, selectionCmd, 'True')
        try:
            _doWriteCommand(scpiObj, selectionCmd, 0)
        except Exception:
            print("\tLimitation values succeed because it raises an exception "
                  "as expected")
        else:
            raise AssertionError("It has been write a value that "
                                 "should not be allowed")
        _interTestWait()
        result = True, "Command writes test PASSED"
    except Exception as e:
        print("\tUnexpected kind of exception! %s" % e)
        print_exc()
        result = False, "Command writes test FAILED"
    _printFooter(result[1])
    return result


def checkNonexistingCommands(scpiObj):
    _printHeader("Testing to query commands that doesn't exist")
    baseCmd = _randomchoice(['SOURce', 'BASIcloop', 'ITERative'])
    subCmd = _randomchoice(['CURRent', 'VOLTage'])
    attr = _randomchoice(['UPPEr', 'LOWEr', 'VALUe'])
    fake = "FAKE"

    start_t = _time()

    pairs = [
        # * first level doesn't exist
        ["%s:%s:%s?" % (fake, subCmd, attr), 'NOK\r\n'],
        # * intermediate level doesn't exist
        ["%s:%s:%s?" % (baseCmd, fake, attr), 'NOK\r\n'],
        # * Attribute level doesn't exist
        ["%s:%s:%s?" % (baseCmd, subCmd, fake), 'NOK\r\n'],
        # * Attribute that doesn't respond
        ['source:voltage:exception', 'NOK\r\n'],
        # * Unexisting Channel
        ["CHANnel%s" % (str(nChannels+3).zfill(2)), 'NOK\r\n'],
        # * Channel below the minimum reference
        ["CHANnel00:VOLTage:UPPEr?", 'NOK\r\n'],
        # * Channel above the maximum reference
        ["CHANnel99:VOLTage:UPPEr?", 'NOK\r\n'],
    ]
    correct, failed = 0, 0

    for cmd, expected_answer in pairs:
        answer = ''
        try:
            start_t = _time()
            answer = _send2Input(
                scpiObj, cmd, expected_answer=expected_answer)
            correct += 1
        except ValueError as exc:
            print("\tFake command answer failed: {0}".format(exc))
            failed += 1
        except Exception as exc:
            print("\tUnexpected kind of exception! {0}".format(exc))
            print_exc()
            failed += 1
        print("\tRequest non-existing command {0}\n"
              "\tAnswer: {1!r} ({2:g} ms)"
              "".format(cmd, answer, (_time()-start_t)*1000))
    if failed == 0:
        result = True, "Non-existing commands test PASSED"
    else:
        print("Failed {0}/{1}".format(failed, correct+failed))
        result = False, "Non-existing commands test FAILED"
    _printFooter(result[1])
    return result


def checkArrayAnswers(scpiObj):
    _printHeader("Requesting an attribute the answer of which is an array")
    try:
        baseCmd = 'source'
        attrCmd = 'buffer'
        longTest = ArrayTest(100)
        scpiObj.add_command(attrCmd, readcb=longTest.readTest)
        # current
        CurrentObj = ArrayTest(5)
        CurrentCmd = "%s:current:%s" % (baseCmd, attrCmd)
        scpiObj.add_command(CurrentCmd, readcb=CurrentObj.readTest)
        # voltage
        VoltageObj = ArrayTest(5)
        VoltageCmd = "%s:voltage:%s" % (baseCmd, attrCmd)
        scpiObj.add_command(VoltageCmd, readcb=VoltageObj.readTest)
        # queries
        answersLengths = {}
        correct, failed = 0, 0
        for cmd in [attrCmd, CurrentCmd, VoltageCmd]:
            for format in ['ASCII', 'QUADRUPLE', 'DOUBLE', 'SINGLE', 'HALF']:
                _send2Input(scpiObj, "DataFormat %s" % (format),
                            check_answer=False)
                answer = None
                try:
                    answer = _send2Input(
                        scpiObj, cmd + '?', bad_answer='NOK\r\n')
                except ValueError as exc:
                    msg = "Error: {0}".format(exc)
                    failed += 1
                else:
                    msg = "Answer: {0!r} (len ({1:d})" \
                          "".format(answer, len(answer))
                    correct += 1
                print("\tRequest {0!r}\n\t{1}\n".format(cmd, msg))
                if format not in answersLengths:
                    answersLengths[format] = []
                answersLengths[format].append(
                    len(answer) if answer is not None else 0)
        print("\tanswer lengths summary: %s"
              % "".join('\n\t\t{}:{}'.format(k, v)
                        for k, v in answersLengths.iteritems()))
        if failed == 0:
            result = True, "Array answers test PASSED"
        else:
            print("Failed {0}/{1}".format(failed, correct+failed))
            result = False, "Array answers test FAILED"
    except Exception as e:
        print("\tUnexpected kind of exception! %s" % e)
        print_exc()
        result = False, "Array answers test FAILED"
    _printFooter(result[1])
    return result


def checkMultipleCommands(scpiObj):
    _printHeader("Requesting more than one attribute per query")
    try:
        log = {}
        correct, failed = 0, 0
        for i in range(2, concatenatedCmds+1):
            lst = []
            for j in range(i):
                lst.append(_buildCommand2Test())
            cmds = "".join("%s;" % x for x in lst)[:-1]
            cmdsSplitted = "".join("\t\t%s\n" % cmd for cmd in cmds.split(';'))
            start_t = _time()
            answer = _send2Input(scpiObj, cmds)
            answers = _cutMultipleAnswer(answer)
            nAnswers = len(answers)
            if '' in answers or 'ACK' in answers or 'NOK' in answers:
                failed += 1
            else:
                correct += 1
            log[nAnswers] = (_time() - start_t)*1000
            print("\tRequest {0:d} attributes in a single query: \n"
                  "{1}\tAnswer: {2!r} ({3:d}, {4:g} ms)\n"
                  "".format(i, cmdsSplitted, answer, nAnswers, log[nAnswers]))
            if nAnswers != i:
                raise AssertionError(
                    "The answer doesn't have the {0:d} expected elements "
                    "(but {1:d})"
                    "".format(i, nAnswers))
            _interTestWait()
        msg = "\tSummary:"
        for length in log:
            t = log[length]
            msg += "\n\t\t{0}\t{1:6.3f} ms\t{2:6.3f} ms/cmd" \
                   "".format(length, t, t/length)
        print(msg)
        if failed == 0:
            result = True, "Many commands per query test PASSED"
        else:
            print("Failed {0}/{1}".format(failed, correct+failed))
            result = False, "Many commands per query test FAILED"
        # TODO: multiple writes
    except Exception as exc:
        print("\tUnexpected kind of exception! {0}".format(exc))
        print_exc()
        result = False, "Many commands per query test FAILED"
    _printFooter(result[1])
    return result


def checkReadWithParams(scpiObj):
    _printHeader("Attribute read with parameters after the '?'")
    try:
        cmd = 'reader:with:parameters'
        longTest = ArrayTest(100)
        scpiObj.add_command(cmd, readcb=longTest.readRange)
        answer = _send2Input(scpiObj, "DataFormat ASCII", check_answer=False)
        correct, failed = 0, 0
        for i in range(10):
            bar, foo = _randint(0, 100), _randint(0, 100)
            start = min(bar, foo)
            end = max(bar, foo)
            # introduce a ' ' (write separator) after the '?' (read separator)
            cmdWithParams = "%s?%3s,%s" % (cmd, start, end)
            try:
                answer = _send2Input(
                    scpiObj, cmdWithParams, bad_answer='NOK\r\n')
            except ValueError as exc:
                msg = "Error: {0}".format(exc)
                failed += 1
            else:
                msg = "Answer: {0!r} (len ({1:d})" \
                      "".format(answer, len(answer))
                correct += 1
            print("\tRequest {0!r}\n\t{1}\n".format(cmdWithParams, msg))
            if answer is None or len(answer) == 0:
                raise ValueError("Empty string")
        cmdWithParams = "%s?%s,%s" % (cmd, start, end)
        if failed == 0:
            result = True, "Read with parameters test PASSED"
        else:
            print("Failed {0}/{1}".format(failed, correct+failed))
            result = False, "Read with parameters test FAILED"
    except Exception as e:
        print("\tUnexpected kind of exception! %s" % e)
        print_exc()
        result = False, "Read with parameters test FAILED"
    _printFooter(result[1])
    return result


def checkWriteWithoutParams(scpiObj):
    _printHeader("Attribute write without parameters")
    try:
        cmd = 'writter:without:parameters'
        switch = WattrTest()
        scpiObj.add_command(cmd, readcb=switch.switchTest)
        correct, failed = 0, 0
        for i in range(3):
            cmd = "%s%s" % (cmd, " "*i)
            try:
                answer = _send2Input(scpiObj, cmd, expected_answer='ACK\r\n')
            except ValueError as exc:
                msg = "Error: {0}".format(exc)
                failed += 1
            else:
                msg = "Answer: {0!r} (len ({1:d})" \
                      "".format(answer, len(answer))
                correct += 1
            print("\tRequest {0!r}\n\t{1}\n".format(cmd, msg))
        if failed == 0:
            result = True, "Write without parameters test PASSED"
        else:
            print("Failed {0}/{1}".format(failed, correct+failed))
            result = False, "Write without parameters test FAILED"
    except Exception as e:
        print("\tUnexpected kind of exception! %s" % e)
        print_exc()
        result = False, "Write without parameters test FAILED"
    _printFooter(result[1])
    return result


def checkLocks(scpiObj):
    _printHeader("system [write]lock")
    try:
        LockThreadedTest(scpiObj).launchTest()
        result = True, "system [write]lock test PASSED"
    except Exception as e:
        print("\tUnexpected kind of exception! %s" % e)
        print_exc()
        result = False, "system [write]lock test FAILED"
    _printFooter(result[1])
    return result


def checkTelnetHooks(scpiObj):
    _printHeader("Telnet hooks")
    try:
        ipv4 = Telnet("127.0.0.1", 5025)
        ipv6 = Telnet("::1", 5025)
        cmd = "*IDN?"

        def hook(who, what):
            _printInfo("\t\thook call, received: (%r, %r)" % (who, what))
        scpiObj.addConnectionHook(hook)
        _printInfo("\tipv4 send %s" % (cmd))
        ipv4.write(cmd)
        _printInfo("\tipv4 answer %r" % ipv4.read_until('\n'))
        _printInfo("\tipv6 send %s" % (cmd))
        ipv6.write(cmd)
        _printInfo("\tipv6 answer %r" % ipv6.read_until('\n'))
        scpiObj.removeConnectionHook(hook)
        ipv4.close()
        ipv6.close()
        result = True, "Telnet hooks test PASSED"
    except Exception as e:
        print("\tUnexpected kind of exception! %s" % e)
        print_exc()
        result = False, "Telnet hooks test FAILED"
    _printFooter(result[1])
    return result

# second descendant level for tests ---


def _send2Input(scpiObj, msg, requestor='local',
                check_answer=True, expected_answer=None, bad_answer=None):
    answer = scpiObj.input(msg)
    if check_answer and (answer is None or len(answer) == 0):
        raise ValueError("Empty string answer for {0}".format(msg))
    if expected_answer is not None and answer != expected_answer:
        raise ValueError(
            "Answer {0!r} doesn't correspond with the expected {1!r} for {2}"
            "".format(answer, expected_answer, msg))
    if bad_answer is not None and answer == bad_answer:
        raise ValueError(
            "Answer {0!r} is not what is expected".format(answer))
    return answer


def _doCheckCommands(scpiObj, baseCmd, innerCmd=None):
    subCmds = ['CURRent', 'VOLTage']
    attrs = ['UPPEr', 'LOWEr', 'VALUe']
    for subCmd in subCmds:
        for attr in attrs:
            if innerCmd:
                cmd = "%s:MEAS:%s:%s:%s?" % (baseCmd, innerCmd, subCmd, attr)
            else:
                cmd = "%s:%s:%s?" % (baseCmd, subCmd, attr)
            answer = _send2Input(scpiObj, cmd)
            print("\tRequest %s of %s (%s)\n\tAnswer: %r"
                  % (attr.lower(), subCmd.lower(), cmd, answer))
    _interTestWait()


def _doWriteCommand(scpiObj, cmd, value=None):
    # first read ---
    answer1 = _send2Input(scpiObj, "%s?" % cmd)
    print("\tRequested %s initial value: %r" % (cmd, answer1))
    # then write ---
    if value is None:
        value = _randint(-1000, 1000)
        while value == int(answer1.strip()):
            value = _randint(-1000, 1000)
    _send2Input(scpiObj, "%s %s" % (cmd, value), check_answer=False)
    print("\tWrite %r value: %r" % (cmd, value))
    # read again ---
    answer2 = _send2Input(scpiObj, "%s?" % cmd)
    print("\tRequested %r again value: %r\n" % (cmd, answer2))
    if answer1 == answer2:
        raise AssertionError("Didn't change after write (%r, %r)"
                             % (answer1, answer2))


def _doWriteChannelCommand(scpiObj, pre, inner, post, nCh, value=None):
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
    answer = _send2Input(scpiObj, "%s" % rCmd)
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
    answer = _send2Input(scpiObj, "%s" % (wCmd), check_answer=False)
    return answer, wCmd


def _cutMultipleAnswer(answerStr):
    answerStr = answerStr.strip()
    answersLst = []
    while len(answerStr) != 0:
        if answerStr[0] == '#':
            headerSize = int(answerStr[1])
            bodySize = int(answerStr[2:headerSize+2])
            bodyBlock = answerStr[headerSize+2:bodySize+headerSize+2]
            # print("with a headerSize of %d and a bodySize of %s, "
            #       "%d elements in the body" % (headerSize, bodySize,
            #                                    len(bodyBlock)))
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


class _EventWithResult(object):
    def __init__(self):
        super(_EventWithResult, self).__init__()
        self._eventObj = _Event()
        self._eventObj.clear()
        self._results = []

    def set(self):
        self._eventObj.set()

    def isSet(self):
        return self._eventObj.isSet()

    def clear(self):
        self._eventObj.clear()

    def resultsAvailable(self):
        return len(self._results) > 0

    @property
    def result(self):
        if self.resultsAvailable():
            return self._results.pop(0)

    @result.setter
    def result(self, value):
        self._results.append(value)


class LockThreadedTest(object):
    def __init__(self, scpiObj):
        super(LockThreadedTest, self).__init__()
        self._scpiObj = scpiObj
        self._printLock = _Lock()
        self._prepareCommands()
        self._prepareClients()

    def _prepareCommands(self):
        self._commands = {'baseCmd': "SOURce:CURRent",
                          'requestRW': "SYSTEM:LOCK:REQUEST?",
                          'requestWO': "SYSTEM:WLOCK:REQUEST?",
                          'releaseRW': "SYSTEM:LOCK:RELEASE?",
                          'releaseWO': "SYSTEM:WLOCK:RELEASE?",
                          'ownerRW': "SYSTEM:LOCK?",
                          'ownerWO': "SYSTEM:WLOCK?"}
        self._readCmd = "%s:LOWEr?;%s?;%s:UPPEr?;%s;%s"\
            % (self._commands['baseCmd'], self._commands['baseCmd'],
               self._commands['baseCmd'],
               self._commands['ownerRW'], self._commands['ownerWO'])
        self._writeCmd = "%s:LOWEr %%s;%s:UPPEr %%s;%s;%s"\
            % (self._commands['baseCmd'],  self._commands['baseCmd'],
               self._commands['ownerRW'], self._commands['ownerWO'])

    def _prepareClients(self):
        self._joinerEvent = _Event()
        self._joinerEvent.clear()
        self._clientThreads = {}
        # use threading.Event() to command the threads to do actions
        self._requestRWlock = {}
        self._requestWOlock = {}
        self._readAccess = {}
        self._writeAccess = {}
        self._releaseRWlock = {}
        self._releaseWOlock = {}
        for threadName in [4, 6]:
            requestRW = _EventWithResult()
            requestWO = _EventWithResult()
            readAction = _EventWithResult()
            writeAction = _EventWithResult()
            releaseRW = _EventWithResult()
            releaseWO = _EventWithResult()
            threadObj = _Thread(target=self._clientThread,
                                args=(threadName,),
                                name="IPv%d" % threadName)
            self._requestRWlock[threadName] = requestRW
            self._requestWOlock[threadName] = requestWO
            self._readAccess[threadName] = readAction
            self._writeAccess[threadName] = writeAction
            self._releaseRWlock[threadName] = releaseRW
            self._releaseWOlock[threadName] = releaseWO
            self._clientThreads[threadName] = threadObj
            threadObj.start()

    def launchTest(self):
        self._test1()  # read access
        self._test2()  # write access
        self._test3()  # write access lock
        self._test4()  # request a lock whe it's owned by another.
        # TODO 5th test: non-owner release.
        # TODO 6th test: take the READ lock when WRITE is taken
        # TODO 7th test: wait until the lock expires and access
        # TODO 8th test: release the WRITE lock
        # TODO 9th test: take the READ lock and clients check the owner
        self._joinerEvent.set()
        while len(self._clientThreads.keys()) > 0:
            threadKey = self._clientThreads.keys()[0]
            clientThread = self._clientThreads.pop(threadKey)
            clientThread.join(1)
            if clientThread.is_alive():
                self._clientThreads[threadKey] = clientThread

    def _test1(self, subtest=0):  # 1st test: read access
        testName = "Clients read access"
        self._print(testName, level=1+subtest, top=True)
        results = self._doReadAll()
        self._printResults(results)
        self._print(testName, level=1+subtest, bottom=True)

    def _test2(self, subtest=0):  # 2nd test: write access
        testName = "Clients write access"
        self._print(testName, level=1+subtest, top=True)
        succeed = {}
        for threadName in self._clientThreads.keys():
            succeed[threadName] = False
            self._writeAccess[threadName].set()
            while self._writeAccess[threadName].isSet():
                _sleep(1)
            readResults = self._doReadAll()
            for tName in readResults.keys():
                self._print("Thread %d: read: %r"
                            % (tName, readResults[tName]), level=2)
        results = self._wait4Results(self._writeAccess, succeed)
        self._printResults(results)
        self._print(testName, level=1+subtest, bottom=True)

    def _test3(self):  # 3rd test: write access lock
        testName = "One Client LOCK the WRITE access"
        self._print(testName, level=1, top=True)
        self._requestWOlock[4].set()
        while self._requestWOlock[4].isSet():
            _sleep(1)
        self._print("Thread 4 should have the lock. Answer: %r"
                    % (self._requestWOlock[4].result), level=2)
        # self._test1(subtest=1)
        # self._test2(subtest=1)
        self._print(testName, level=1, bottom=True)

    def _test4(self):  # 3rd test: request a lock whe it's owned by another
        testName = "Another Client request LOCK the WRITE access "\
            "(when still is owned by another)"
        self._print(testName, level=1, top=True)
        self._requestWOlock[6].set()
        while self._requestWOlock[6].isSet():
            _sleep(1)
        self._print("Thread 4 should have the lock and thread 6 NOT. "
                    "Answer: %r" % (self._requestWOlock[6].result), level=2)
        # self._test1(subtest=1)
        self._print(testName, level=1, bottom=True)

    def _doReadAll(self):
        actionDone = {}
        for threadName in self._clientThreads.keys():
            actionDone[threadName] = False
            self._readAccess[threadName].set()
        return self._wait4Results(self._readAccess, actionDone)

    def _wait4Results(self, eventGrp, succeedDct):
        results = {}
        while not all(succeedDct.values()):
            for threadName in self._clientThreads.keys():
                if succeedDct[threadName] is False and \
                        eventGrp[threadName].resultsAvailable():
                    result = eventGrp[threadName].result
                    # TODO: process the result to device if the test has passed
                    succeedDct[threadName] = True
                    results[threadName] = result
            _sleep(0.1)
        return results

    def _clientThread(self, threadName):
        self._print("start", level=0)
        connectionObj = self._buildClientConnection(threadName)
        while not self._joinerEvent.isSet():
            self._checkAction(self._requestRWlock[threadName],
                              'requestRW', connectionObj)
            self._checkAction(self._requestWOlock[threadName],
                              'requestWO', connectionObj)
            # TODO: read and write
            self._checkRead(threadName, connectionObj)
            self._checkWrite(threadName, connectionObj)
            self._checkAction(self._releaseRWlock[threadName],
                              'releaseRW', connectionObj)
            self._checkAction(self._releaseWOlock[threadName],
                              'releaseWO', connectionObj)
            _sleep(0.1)
        connectionObj.close()
        self._print("exit", level=0)

    def _buildClientConnection(self, ipversion):
        if ipversion == 4:
            socket = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
            socket.connect(('127.0.0.1', 5025))
        elif ipversion == 6:
            socket = _socket.socket(_socket.AF_INET6, _socket.SOCK_STREAM)
            socket.connect(('::1', 5025))
        else:
            raise RuntimeError("Cannot build the connection to the server!")
        return socket

    def _checkAction(self, event, eventTag, socket):
        if event.isSet():
            socket.send(self._commands[eventTag])
            event.result = socket.recv(1024)
            event.clear()

    def _checkRead(self, threadName, socket):
        event = self._readAccess[threadName]
        if event.isSet():
            socket.send(self._readCmd)
            event.result = socket.recv(1024)
            event.clear()

    def _checkWrite(self, threadName, socket):
        event = self._writeAccess[threadName]
        if event.isSet():
            socket.send(self._writeCmd % (_randint(-100, 0), _randint(0, 100)))
            event.result = socket.recv(1024)
            event.clear()

    def _printResults(self, results):
        for threadName in results.keys():
            self._print("Thread %d report: %r"
                        % (threadName, results[threadName]))

    def _print(self, msg, level=1, top=False, bottom=False):
        _printInfo(msg, level=level, lock=self._printLock, top=top,
                   bottom=bottom)


def main():
    import traceback
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('', "--debug", action="store_true", default=False,
                      help="Set the debug flag")
    parser.add_option('', "--pause", action="store_true", default=False,
                      help="Pause after each of the tests")
    parser.add_option('--no-remove', dest='no_remove', action="store_true",
                      help="don't destroy the test until the user say")
    (options, args) = parser.parse_args()
    scpi_timeit_collection(True)
    for test in [testScpi]:
        try:
            test(options.debug, options.pause, options.no_remove)
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
