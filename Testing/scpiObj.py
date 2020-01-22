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


from _objects import AttrTest, ArrayTest
from _objects import ChannelTest, SubchannelTest
from _objects import n_channels, n_subchannels
from _objects import WattrTest, WchannelTest
from _printing import print_header as _print_header
from _printing import print_footer as _print_footer
from _printing import print_info as _print_info
from random import choice as _random_choice
from random import randint as _randint
from sys import stdout as _stdout
from scpilib import scpi
from scpilib.version import version as _version
from scpilib.logger import scpi_timeit_collection, scpi_log2file
import socket as _socket
from telnetlib import Telnet
from time import sleep as _sleep
from time import time as _time
from threading import Event as _Event
from threading import Lock as _Lock
from threading import Thread as _Thread
from traceback import print_exc


class InstrumentIdentification(object):
    def __init__(self, manufacturer, instrument, serial_number,
                 firmware_version):
        object.__init__(self)
        self.manufacturer = manufacturer
        self.instrument = instrument
        self.serial_number = serial_number
        self.firmware_version = firmware_version

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
    def serial_number(self):
        return self._serial_number

    @serial_number.setter
    def serial_number(self, value):
        self._serial_number = str(value)

    @property
    def firmware_version(self):
        return self._firmware_version

    @firmware_version.setter
    def firmware_version(self, value):
        self._firmware_version = str(value)

    def idn(self):
        return "{0},{1},{2},{3}".format(self.manufacturer, self.instrument,
                                    self.serial_number, self.firmware_version)


stepTime = .1
concatenated_cmds = 50
wait_msg = "wait..."


def _wait(t):
    _stdout.write(wait_msg)
    _stdout.flush()
    _sleep(t)
    _stdout.write("\r"+" "*len(wait_msg)+"\r")
    _stdout.flush()


def _inter_test_wait():
    _wait(stepTime)


def _after_test_wait(pause, msg=None, wait_time=None):
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


def test_scpi(debug, pause, no_remove):
    start_t = _time()
    _print_header("Testing scpi main class (version {0})".format(_version()))
    # ---- BuildSpecial('IDN',specialSet,identity.idn)
    with scpi(local=True, debug=debug, write_lock=True) as scpi_obj:
        print("Log information: {0}".format(scpi_obj.loggingFile()))
        results = []
        result_msgs = []
        try:
            for test in [
                check_idn,
                add_invalid_cmds,
                add_valid_commands,
                check_command_queries,
                check_command_writes,
                check_nonexisting_commands,
                check_array_answers,
                check_multiple_commands,
                check_read_with_params,
                check_write_without_params,
                # check_locks,
                # check_telnet_hooks,
            ]:
                result, msg = test(scpi_obj)
                results.append(result)
                tag, value = msg.rsplit(' ', 1)
                result_msgs.append([tag, value])
                if _after_test_wait(pause) is False:
                    break
        except KeyboardInterrupt:
            print("Test interrupted...")
        txt = "Tests completed (Ctrl+c to print the summary and end)"
        _after_test_wait(no_remove, msg=txt, wait_time=0)
    if all(results):
        _print_header("All tests passed: everything OK ({:g} s)"
                      "".format(_time()-start_t))
    else:
        _print_header("ALERT!! NOT ALL THE TESTS HAS PASSED. Check the list "
                      "({:g} s)".format(_time()-start_t))
    length = 0
    for pair in result_msgs:
        if len(pair[0]) > length:
            length = len(pair[0])
    for result in result_msgs:
        print("{0}{1}\t{2}{3}".format(
            result[0], " "*(length-len(result[0])),
            result[1], " *" if result[1] == 'FAILED' else ""))
    print("")


# First descendant level for tests ---


def check_idn(scpi_obj):
    _print_header("Test instrument identification")
    try:
        identity = InstrumentIdentification('ALBA', 'test', 0, _version())
        scpi_obj.add_special_command('IDN', identity.idn)
        cmd = "*idn?"
        answer = _send2input(scpi_obj, cmd)
        print("\tRequest identification: {0}\n\tAnswer: {1!r}"
              "".format(cmd, answer))
        if answer.strip() != identity.idn():
            result = False, "Identification test FAILED"
        else:
            result = True, "Identification test PASSED"
    except Exception as exp:
        print("\tUnexpected kind of exception! {0}".format(exp))
        print_exc()
        result = False, "Identification test FAILED"
    _print_footer(result[1])
    return result


def add_invalid_cmds(scpi_obj):
    _print_header("Testing to build invalid commands")
    try:
        scpi_obj.add_command(":startswithcolon", read_cb=None)
    except NameError as exc:
        print("\tNull name test PASSED")
    except Exception as exc:
        print("\tUnexpected kind of exception! {0}".format(exc))
        print_exc()
        return False, "Invalid commands test FAILED"
    try:
        scpi_obj.add_command("double::colons", read_cb=None)
    except NameError:
        print("\tDouble colon name test PASSED")
    except Exception as exc:
        print("\tUnexpected kind of exception! {0}".format(exc))
        print_exc()
        return False, "Invalid commands test FAILED"
    try:
        scpi_obj.add_command("nestedSpecial:*special", read_cb=None)
    except NameError:
        scpi_obj.command_tree.pop('nestedSpecial')
        print("\tNested special command test PASSED")
    except Exception as exp:
        print("\tUnexpected kind of exception! {0}".format(exc))
        print_exc()
        return False, "Invalid commands test FAILED"
    result = True, "Invalid commands test PASSED"
    _print_footer(result[1])
    return result


def add_valid_commands(scpi_obj):
    _print_header("Testing to build valid commands")
    try:
        # ---- valid commands section
        current_obj = AttrTest()
        voltage_obj = AttrTest()
        # * commands can de added by telling their full name:
        scpi_obj.add_command('source:current:upper',
                             read_cb=current_obj.upperLimit,
                             write_cb=current_obj.upperLimit)
        scpi_obj.add_command('source:current:lower',
                             read_cb=current_obj.lowerLimit,
                             write_cb=current_obj.lowerLimit)
        scpi_obj.add_command('source:current:value',
                             read_cb=current_obj.readTest,
                             default=True)
        scpi_obj.add_command('source:voltage:upper',
                             read_cb=voltage_obj.upperLimit,
                             write_cb=voltage_obj.upperLimit)
        scpi_obj.add_command('source:voltage:lower',
                             read_cb=voltage_obj.lowerLimit,
                             write_cb=voltage_obj.lowerLimit)
        scpi_obj.add_command('source:voltage:value', 
                             read_cb=voltage_obj.readTest, default=True)
        scpi_obj.add_command('source:voltage:exception',
                             read_cb=voltage_obj.exceptionTest)
        # * They can be also created in an iterative way
        base_cmd_name = 'basicloop'
        for (sub_cmd_name, sub_cmd_obj) in [('current', current_obj),
                                            ('voltage', voltage_obj)]:
            for (attr_name, attr_func) in [('upper', 'upperLimit'),
                                           ('lower', 'lowerLimit'),
                                           ('value', 'readTest')]:
                if hasattr(sub_cmd_obj, attr_func):
                    cb_func = getattr(sub_cmd_obj, attr_func)
                    if attr_name == 'value':
                        default = True
                    else:
                        default = False
                    scpi_obj.add_command("{0}:{1}:{2}".format(
                        base_cmd_name, sub_cmd_name, attr_name),
                        read_cb=cb_func, default=default)
                    # Basically is the same than the first example,
                    # but the add_command is constructed with variables
                    # in nested loops
        # * Another alternative to create the tree in an iterative way would be
        it_cmd = 'iterative'
        it_obj = scpi_obj.add_component(it_cmd, scpi_obj.command_tree)
        for (subcomponent, sub_cmd_obj) in [('current', current_obj),
                                            ('voltage', voltage_obj)]:
            subcomponent_obj = scpi_obj.add_component(subcomponent, it_obj)
            for (attr_name, attr_func) in [('upper', 'upperLimit'),
                                           ('lower', 'lowerLimit'),
                                           ('value', 'readTest')]:
                if hasattr(sub_cmd_obj, attr_func):
                    cb_func = getattr(sub_cmd_obj, attr_func)
                    if attr_name == 'value':
                        default = True
                    else:
                        default = False
                    attr_obj = scpi_obj.add_attribute(
                        attr_name, subcomponent_obj, cb_func, default=default)
                else:
                    print("{0} hasn't {1}".format(subcomponent_obj, attr_func))
                    # In this case, the intermediate objects of the tree are
                    # build and it is in the inner loop where they have the
                    # attributes created.
                    #  * Use with very big care this option because the library
                    #  * don't guarantee that all the branches of the tree will
                    #  * have the appropriate leafs.
        # * Example of how can be added a node with channels in the scpi tree
        ch_cmd = 'channel'
        ch_obj = scpi_obj.add_channel(ch_cmd, n_channels, scpi_obj.command_tree)
        ch_current_obj = ChannelTest(n_channels)
        ch_voltage_obj = ChannelTest(n_channels)
        for (subcomponent, sub_cmd_obj) in [('current', ch_current_obj),
                                            ('voltage', ch_voltage_obj)]:
            subcomponent_obj = scpi_obj.add_component(subcomponent, ch_obj)
            for (attr_name, attr_func) in [('upper', 'upperLimit'),
                                           ('lower', 'lowerLimit'),
                                           ('value', 'readTest')]:
                if hasattr(sub_cmd_obj, attr_func):
                    cb_func = getattr(sub_cmd_obj, attr_func)
                    if attr_name == 'value':
                        default = True
                    else:
                        default = False
                    attr_obj = scpi_obj.add_attribute(attr_name, subcomponent_obj,
                                                      cb_func, default=default)
        # * Example of how can be nested channel type components in a tree that
        #   already have this channels componets defined.
        meas_cmd = 'measurements'
        meas_obj = scpi_obj.add_component(meas_cmd, ch_obj)
        fn_cmd = 'function'
        fn_obj = scpi_obj.add_channel(fn_cmd, n_subchannels, meas_obj)
        chfn_current_obj = SubchannelTest(n_channels, n_subchannels)
        chfn_voltage_obj = SubchannelTest(n_channels, n_subchannels)
        for (subcomponent, sub_cmd_obj) in [('current', chfn_current_obj),
                                            ('voltage', chfn_voltage_obj)]:
            subcomponent_obj = scpi_obj.add_component(subcomponent, fn_obj)
            for (attr_name, attr_func) in [('upper', 'upperLimit'),
                                           ('lower', 'lowerLimit'),
                                           ('value', 'readTest')]:
                if hasattr(sub_cmd_obj, attr_func):
                    cb_func = getattr(sub_cmd_obj, attr_func)
                    if attr_name == 'value':
                        default = True
                    else:
                        default = False
                    attr_obj = scpi_obj.add_attribute(attr_name, subcomponent_obj,
                                                      cb_func, default=default)
        print("Command tree build: {!r}".format(scpi_obj.command_tree))
        result = True, "Valid commands test PASSED"
        # TODO: channels with channels until the attributes
    except Exception as exc:
        print("\tUnexpected kind of exception! {0}".format(exc))
        print_exc()
        result = False, "Valid commands test FAILED"
    _print_footer(result[1])
    return result


def check_command_queries(scpi_obj):
    _print_header("Testing to command queries")
    try:
        print("Launch tests:")
        cmd = "*IDN?"
        answer = _send2input(scpi_obj, cmd)
        print("\tInstrument identification ({0})\n\tAnswer: {1}"
              "".format(cmd, answer))
        for base_cmd in ['SOURce', 'BASIcloop', 'ITERative']:
            _print_header("Check {0} part of the tree".format(base_cmd))
            _do_check_commands(scpi_obj, base_cmd)
        for ch in range(1, n_channels+1):
            base_cmd = "CHANnel{0}".format(str(ch).zfill(2))
            _print_header("Check {0} part of the tree".format(base_cmd))
            _do_check_commands(scpi_obj, base_cmd)
            fn = _random_choice(range(1, n_subchannels+1))
            inner_cmd = "FUNCtion{0}".format(str(fn).zfill(2))
            _print_header("Check {0} + MEAS:{1} part of the tree"
                          "".format(base_cmd, inner_cmd))
            _do_check_commands(scpi_obj, base_cmd, inner_cmd)
        result = True, "Command queries test PASSED"
    except Exception as exc:
        print("\tUnexpected kind of exception! {0}".format(e))
        print_exc()
        result = False, "Command queries test FAILED"
    _print_footer(result[1])
    return result


def check_command_writes(scpi_obj):
    _print_header("Testing to command writes")
    try:
        # simple commands ---
        current_conf_obj = WattrTest()
        scpi_obj.add_command('source:current:configure',
                             read_cb=current_conf_obj.readTest,
                             write_cb=current_conf_obj.writeTest)
        voltage_conf_obj = WattrTest()
        scpi_obj.add_command('source:voltage:configure',
                             read_cb=voltage_conf_obj.readTest,
                             write_cb=voltage_conf_obj.writeTest)
        for inner in ['current', 'voltage']:
            _do_write_command(scpi_obj, "source:{0}:configure".format(inner))
        _wait(1)  # FIXME: remove
        # channel commands ---
        _print_header("Testing to channel command writes")
        base_cmd = 'writable'
        w_obj = scpi_obj.add_component(base_cmd, scpi_obj.command_tree)
        ch_cmd = 'channel'
        ch_obj = scpi_obj.add_channel(ch_cmd, n_channels, w_obj)
        ch_current_obj = WchannelTest(n_channels)
        ch_voltage_obj = WchannelTest(n_channels)
        for (subcomponent, sub_cmd_obj) in [('current', ch_current_obj),
                                            ('voltage', ch_voltage_obj)]:
            subcomponent_obj = scpi_obj.add_component(subcomponent, ch_obj)
            for (attr_name, attr_func) in [('upper', 'upperLimit'),
                                           ('lower', 'lowerLimit'),
                                           ('value', 'readTest')]:
                if hasattr(sub_cmd_obj, attr_func):
                    if attr_name == 'value':
                        attr_obj = scpi_obj.add_attribute(
                            attr_name, subcomponent_obj,
                            read_cb=sub_cmd_obj.readTest,
                            write_cb=sub_cmd_obj.writeTest, default=True)
                    else:
                        cb_func = getattr(sub_cmd_obj, attr_func)
                        attr_obj = scpi_obj.add_attribute(
                            attr_name, subcomponent_obj, cb_func)
        print("\nChecking one write multiple reads\n")
        for i in range(n_channels):
            rnd_ch = _randint(1, n_channels)
            element = _random_choice(['current', 'voltage'])
            _do_write_channel_command(
                scpi_obj, "{0}:{1}".format(base_cmd, ch_cmd), rnd_ch,
                element, n_channels)
            _inter_test_wait()
        print("\nChecking multile writes multiple reads\n")
        for i in range(n_channels):
            test_nwrites = _randint(2, n_channels)
            rnd_chs = []
            while len(rnd_chs) < test_nwrites:
                rnd_ch = _randint(1, n_channels)
                while rnd_ch in rnd_chs:
                    rnd_ch = _randint(1, n_channels)
                rnd_chs.append(rnd_ch)
            element = _random_choice(['current', 'voltage'])
            values = [_randint(-1000, 1000)]*test_nwrites
            _do_write_channel_command(
                scpi_obj, "{0}:{1}".format(base_cmd, ch_cmd), rnd_chs,
                element, n_channels, values)
            _inter_test_wait()
        print("\nChecking write with allowed values limitation\n")
        selection_cmd = 'source:selection'
        selection_obj = WattrTest()
        selection_obj.writeTest(False)
        scpi_obj.add_command(selection_cmd, read_cb=selection_obj.readTest,
                             write_cb=selection_obj.writeTest,
                             allowed_argins=[True, False])
        _do_write_command(scpi_obj, selection_cmd, True)
        # _do_write_command(scpi_obj, selection_cmd, 'Fals')
        # _do_write_command(scpi_obj, selection_cmd, 'True')
        try:
            _do_write_command(scpi_obj, selection_cmd, 0)
        except Exception:
            print("\tLimitation values succeed because it raises an exception "
                  "as expected")
        else:
            raise AssertionError("It has been write a value that "
                                 "should not be allowed")
        _inter_test_wait()
        result = True, "Command writes test PASSED"
    except Exception as exc:
        print("\tUnexpected kind of exception! {0}".format(exc))
        print_exc()
        result = False, "Command writes test FAILED"
    _print_footer(result[1])
    return result


def check_nonexisting_commands(scpi_obj):
    _print_header("Testing to query commands that doesn't exist")
    base_cmd = _random_choice(['SOURce', 'BASIcloop', 'ITERative'])
    sub_cmd = _random_choice(['CURRent', 'VOLTage'])
    attr = _random_choice(['UPPEr', 'LOWEr', 'VALUe'])
    fake = "FAKE"
    ack = 'ACK\r\n'
    nok = 'NOK\r\n'

    start_t = _time()

    pairs = [
        # * first level doesn't exist
        ["{0}:{1}:{2}?".format(fake, sub_cmd, attr), nok],
        # * intermediate level doesn't exist
        ["{0}:{1}:{2}?".format(base_cmd, fake, attr), nok],
        # * Attribute level doesn't exist
        ["{0}:{1}:{2}?".format(base_cmd, sub_cmd, fake), nok],
        # * Attribute that doesn't respond
        ['source:voltage:exception?', nok],
        # * Unexisting Channel
        ["CHANnel{0}".format(str(n_channels+3).zfill(2)), nok],
        # * Channel below the minimum reference
        ["CHANnel00:VOLTage:UPPEr?", nok],
        # * Channel above the maximum reference
        ["CHANnel99:VOLTage:UPPEr?", nok],
    ]
    correct, failed = 0, 0

    for cmd, expected_answer in pairs:
        answer = ''
        try:
            start_t = _time()
            answer = _send2input(
                scpi_obj, cmd, expected_answer=expected_answer)
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
    _print_footer(result[1])
    return result


def check_array_answers(scpi_obj):
    _print_header("Requesting an attribute the answer of which is an array")
    try:
        base_cmd = 'source'
        attr_cmd = 'buffer'
        long_test = ArrayTest(100)
        scpi_obj.add_command(attr_cmd, read_cb=long_test.readTest)
        # current
        current_obj = ArrayTest(5)
        current_cmd = "{0}:current:{1}".format(base_cmd, attr_cmd)
        scpi_obj.add_command(current_cmd, read_cb=current_obj.readTest)
        # voltage
        voltage_obj = ArrayTest(5)
        voltage_cmd = "{0}:voltage:{1}".format(base_cmd, attr_cmd)
        scpi_obj.add_command(voltage_cmd, read_cb=voltage_obj.readTest)
        # queries
        answers_lengths = {}
        correct, failed = 0, 0
        for cmd in [attr_cmd, current_cmd, voltage_cmd]:
            for format in ['ASCII', 'QUADRUPLE', 'DOUBLE', 'SINGLE', 'HALF']:
                _send2input(scpi_obj, "DataFormat {0}".format(format),
                            check_answer=False)
                answer = None
                try:
                    answer = _send2input(
                        scpi_obj, cmd + '?', bad_answer='NOK\r\n')
                except ValueError as exc:
                    msg = "Error: {0}".format(exc)
                    failed += 1
                else:
                    msg = "Answer: {0!r} (len ({1:d})" \
                          "".format(answer, len(answer))
                    correct += 1
                print("\tRequest {0!r}\n\t{1}\n".format(cmd, msg))
                if format not in answers_lengths:
                    answers_lengths[format] = []
                answers_lengths[format].append(
                    len(answer) if answer is not None else 0)
        print("\tanswer lengths summary: {0}".format(
            "".join('\n\t\t{0}:{1}'.format(k, v)
                    for k, v in answers_lengths.iteritems())))
        if failed == 0:
            result = True, "Array answers test PASSED"
        else:
            print("Failed {0}/{1}".format(failed, correct+failed))
            result = False, "Array answers test FAILED"
    except Exception as e:
        print("\tUnexpected kind of exception! {0}".format(e))
        print_exc()
        result = False, "Array answers test FAILED"
    _print_footer(result[1])
    return result


def check_multiple_commands(scpi_obj):
    _print_header("Requesting more than one attribute per query")
    try:
        log = {}
        correct, failed = 0, 0
        for i in range(2, concatenated_cmds+1):
            lst = []
            for j in range(i):
                bar = _build_command2test()
                lst.append(bar)
            cmds = ";".join(x for x in lst)
            cmds_repr = "".join("\t\t{0}\n".format(cmd)
                                    for cmd in cmds.split(';'))
            start_t = _time()
            answer = _send2input(scpi_obj, cmds)
            answers = _cut_multiple_answer(answer)
            n_answers = len(answers)
            if '' in answers or 'ACK' in answers or 'NOK' in answers:
                failed += 1
            else:
                correct += 1
            log[n_answers] = (_time() - start_t)*1000
            print("\tRequest {0:d} attributes in a single query: \n"
                  "{1}\tAnswer: {2!r} ({3:d}, {4:g} ms)\n"
                  "".format(i, cmds_repr, answer, n_answers, log[n_answers]))
            if n_answers != i:
                raise AssertionError(
                    "The answer doesn't have the {0:d} expected elements "
                    "(but {1:d})"
                    "".format(i, n_answers))
            _inter_test_wait()
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
    _print_footer(result[1])
    return result


def check_read_with_params(scpi_obj):
    _print_header("Attribute read with parameters after the '?'")
    try:
        cmd = 'reader:with:parameters'
        long_test = ArrayTest(100)
        scpi_obj.add_command(cmd, read_cb=long_test.readRange)
        answer = _send2input(scpi_obj, "DataFormat ASCII", check_answer=False)
        correct, failed = 0, 0
        for i in range(10):
            bar, foo = _randint(0, 100), _randint(0, 100)
            start = min(bar, foo)
            end = max(bar, foo)
            # introduce a ' ' (write separator) after the '?' (read separator)
            cmd_with_params = "{0}?{1:>3},{2}".format(cmd, start, end)
            try:
                answer = _send2input(
                    scpi_obj, cmd_with_params, bad_answer='NOK\r\n')
            except ValueError as exc:
                msg = "Error: {0}".format(exc)
                failed += 1
            else:
                msg = "Answer: {0!r} (len ({1:d})" \
                      "".format(answer, len(answer))
                correct += 1
            print("\tRequest {0!r}\n\t{1}\n".format(cmd_with_params, msg))
            if answer is None or len(answer) == 0:
                raise ValueError("Empty string")
        cmd_with_params = "{0}?{1},{2}".format(cmd, start, end)
        if failed == 0:
            result = True, "Read with parameters test PASSED"
        else:
            print("Failed {0}/{1}".format(failed, correct+failed))
            result = False, "Read with parameters test FAILED"
    except Exception as exc:
        print("\tUnexpected kind of exception! {0}".format(exc))
        print_exc()
        result = False, "Read with parameters test FAILED"
    _print_footer(result[1])
    return result


def check_write_without_params(scpi_obj):
    _print_header("Attribute write without parameters")
    try:
        cmd = 'writter:without:parameters'
        switch = WattrTest()
        scpi_obj.add_command(cmd, read_cb=switch.switchTest)
        correct, failed = 0, 0
        for i in range(3):
            cmd = "{0}{1}".format(cmd, " "*i)
            try:
                answer = _send2input(scpi_obj, cmd, expected_answer='ACK\r\n')
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
    except Exception as exc:
        print("\tUnexpected kind of exception! {0}".format(exc))
        print_exc()
        result = False, "Write without parameters test FAILED"
    _print_footer(result[1])
    return result


def check_locks(scpi_obj):
    _print_header("system [write]lock")
    try:
        LockThreadedTest(scpi_obj).launch_test()
        result = True, "system [write]lock test PASSED"
    except Exception as exc:
        print("\tUnexpected kind of exception! {0}".format(exc))
        print_exc()
        result = False, "system [write]lock test FAILED"
    _print_footer(result[1])
    return result


def check_telnet_hooks(scpi_obj):
    _print_header("Telnet hooks")
    try:
        ipv4 = Telnet("127.0.0.1", 5025)
        ipv6 = Telnet("::1", 5025)
        cmd = "*IDN?"

        def hook(who, what):
            _print_info("\t\thook call, received: ({0!r}, {1!r})"
                        "".format(who, what))
        scpi_obj.addConnectionHook(hook)
        _print_info("\tipv4 send {0}".format(cmd))
        ipv4.write(cmd)
        _print_info("\tipv4 answer {0!r}".format(ipv4.read_until('\n')))
        _print_info("\tipv6 send {0}".format(cmd))
        ipv6.write(cmd)
        _print_info("\tipv6 answer {0!r}".format(ipv6.read_until('\n')))
        scpi_obj.removeConnectionHook(hook)
        ipv4.close()
        ipv6.close()
        result = True, "Telnet hooks test PASSED"
    except Exception as exc:
        print("\tUnexpected kind of exception! {0}".format(exc))
        print_exc()
        result = False, "Telnet hooks test FAILED"
    _print_footer(result[1])
    return result

# second descendant level for tests ---


def _send2input(scpi_obj, msg, requestor='local',
                check_answer=True, expected_answer=None, bad_answer=None):
    answer = scpi_obj.input(msg)
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


def _do_check_commands(scpi_obj, base_cmd, inner_cmd=None):
    sub_cmds = ['CURRent', 'VOLTage']
    attrs = ['UPPEr', 'LOWEr', 'VALUe']
    for sub_cmd in sub_cmds:
        for attr in attrs:
            if inner_cmd:
                cmd = "{0}:MEAS:{1}:{2}:{3}?".format(
                    base_cmd, inner_cmd, sub_cmd, attr)
            else:
                cmd = "{0}:{1}:{2}?".format(base_cmd, sub_cmd, attr)
            answer = _send2input(scpi_obj, cmd)
            print("\tRequest {0} of {1} ({2})\n\tAnswer: {3!r}".format(
                attr.lower(), sub_cmd.lower(), cmd, answer))
    _inter_test_wait()


def _do_write_command(scpi_obj, cmd, value=None):
    # first read ---
    answer1 = _send2input(scpi_obj, "{0}?".format(cmd))
    print("\tRequested {0} initial value: {1!r}".format(cmd, answer1))
    # then write ---
    if value is None:
        value = _randint(-1000, 1000)
        while value == int(answer1.strip()):
            value = _randint(-1000, 1000)
    _send2input(scpi_obj, "{0} {1}".format(cmd, value), check_answer=False)
    print("\tWrite {0!r} value: {1!r}".format(cmd, value))
    # read again ---
    answer2 = _send2input(scpi_obj, "{0}?".format(cmd))
    print("\tRequested {0!r} again value: {1!r}\n".format(cmd, answer2))
    if answer1 == answer2:
        raise AssertionError(
            "Didn't change after write ({0!r}, {1!r})".format(
                answer1, answer2))


def _do_write_channel_command(scpi_obj, pre, inner, post, n_ch, value=None):
    mask_cmd = "{0}NN:{1}".format(pre, post)
    # first read all the channels ---
    answer1, to_modify, value = _channel_cmds_read_check(scpi_obj, pre, inner,
                                                         post, n_ch, value)
    print("\tRequested {0} initial values:\n\t\t{1!r}\n\t\t(highlight {2})"
          "".format(mask_cmd, answer1, to_modify.items()))
    # then write the specified one ---
    answer2, w_cmd = _channel_cmds_write(scpi_obj, pre, inner,
                                         post, n_ch, value)
    print("\tWrite {0} value: {1}, answer:\n\t\t{2!r}"
          "".format(w_cmd, value, answer2))
    # read again all of them ---
    answer3, modified, value = _channel_cmds_read_check(scpi_obj, pre, inner,
                                                        post, n_ch, value)
    print("\tRequested {0} initial values:\n\t\t{1!r}\n\t\t(highlight {2})\n"
          "".format(mask_cmd, answer3, modified.items()))


def _channel_cmds_read_check(scpi_obj, pre, inner, post, n_ch, value=None):
    r_cmd = ''.join("{0}{1}:{2}?;".format(pre, str(ch).zfill(2), post)
                    for ch in range(1, n_ch+1))
    answer = _send2input(scpi_obj, "{0}".format(r_cmd))
    if type(inner) is list:
        to_check = {}
        for i in inner:
            to_check[i] = answer.strip().split(';')[i-1]
    else:
        to_check = {inner: answer.strip().split(';')[inner-1]}
        if value is None:
            value = _randint(-1000, 1000)
            while value == int(to_check[inner]):
                value = _randint(-1000, 1000)
    return answer, to_check, value


def _channel_cmds_write(scpi_obj, pre, inner, post, n_ch, value):
    if type(inner) is list:
        if type(value) is not list:
            value = [value]*len(inner)
        while len(value) < len(inner):
            value += value[-1]
        w_cmd = ""
        for i, each in enumerate(inner):
            w_cmd += "{0}{1}:{2} {3};".format(pre, str(each).zfill(2),
                                              post, value[i])
        w_cmd = w_cmd[:-1]
    else:
        w_cmd = "{0}{1}:{2} {3}".format(pre, str(inner).zfill(2), post, value)
    answer = _send2input(scpi_obj, "{0}".format(w_cmd), check_answer=False)
    return answer, w_cmd


def _cut_multiple_answer(answer_str):
    answer_str = answer_str.strip()
    answers_lst = []
    while len(answer_str) != 0:
        if answer_str[0] == '#':
            header_size = int(answer_str[1])
            body_size = int(answer_str[2:header_size+2])
            body_block = answer_str[header_size+2:body_size+header_size+2]
            # print("with a header_size of {0} and a body_size of {1}, "
            #       "{2} elements in the body".format(header_size, body_size,
            #                                         len(body_block)))
            answer_str = answer_str[2+header_size+body_size:]
            if len(answer_str) > 0:
                answer_str = answer_str[1:]
            answers_lst.append(body_block)
        else:
            if answer_str.count(';'):
                one, answer_str = answer_str.split(';', 1)
            else:  # the last element
                one = answer_str
                answer_str = ''
            answers_lst.append(one)
    return answers_lst


def _build_command2test():
    base_cmds = ['SOURce', 'BASIcloop', 'ITERative', 'CHANnel']
    sub_cmds = ['CURRent', 'VOLTage']
    attrs = ['UPPEr', 'LOWEr', 'VALUe']
    base_cmd = _random_choice(base_cmds)
    if base_cmd in ['CHANnel']:
        base_cmd = "{0}{1}".format(
            base_cmd, str(_randint(1, n_channels)).zfill(2))
        if _randint(0, 1):
            base_cmd = "{0}:MEAS:FUNC{1}" \
                       "".format(base_cmd,
                                 str(_randint(1, n_subchannels)).zfill(2))
    sub_cmd = _random_choice(sub_cmds)
    if base_cmd in ['SOURce']:
        attr = _random_choice(attrs + ['BUFFer'])
    else:
        attr = _random_choice(attrs)
    return "{0}:{1}:{2}?".format(base_cmd, sub_cmd, attr)


class _EventWithResult(object):
    def __init__(self):
        super(_EventWithResult, self).__init__()
        self._event_obj = _Event()
        self._event_obj.clear()
        self._results = []

    def set(self):
        self._event_obj.set()

    def is_set(self):
        return self._event_obj.is_set()

    def clear(self):
        self._event_obj.clear()

    def results_available(self):
        return len(self._results) > 0

    @property
    def result(self):
        if self.results_available():
            return self._results.pop(0)

    @result.setter
    def result(self, value):
        self._results.append(value)


class LockThreadedTest(object):
    def __init__(self, scpi_obj):
        super(LockThreadedTest, self).__init__()
        self._scpi_obj = scpi_obj
        self._print_lock = _Lock()
        self._prepare_commands()
        self._prepare_clients()

    def _prepare_commands(self):
        self._commands = {'base_cmd': "SOURce:CURRent",
                          'request_RW': "SYSTEM:LOCK:REQUEST?",
                          'request_WO': "SYSTEM:WLOCK:REQUEST?",
                          'release_RW': "SYSTEM:LOCK:RELEASE?",
                          'release_WO': "SYSTEM:WLOCK:RELEASE?",
                          'ownerRW': "SYSTEM:LOCK?",
                          'ownerWO': "SYSTEM:WLOCK?"}
        self._read_cmd = "{0}:LOWEr?;{1}?;{2}:UPPEr?;{3};{4}" \
                        "".format(self._commands['base_cmd'],
                                  self._commands['base_cmd'],
                                  self._commands['base_cmd'],
                                  self._commands['ownerRW'],
                                  self._commands['ownerWO'])
        self._write_cmd = "%s:LOWEr %%s;%s:UPPEr %%s;%s;%s"\
            % (self._commands['base_cmd'],  self._commands['base_cmd'],
               self._commands['ownerRW'], self._commands['ownerWO'])
        # FIXME: review those %%s to modify the string formating
        #  from C like to pythonic one

    def _prepare_clients(self):
        self._joiner_event = _Event()
        self._joiner_event.clear()
        self._client_threads = {}
        # use threading.Event() to command the threads to do actions
        self._request_RW_lock = {}
        self._request_WO_lock = {}
        self._read_access = {}
        self._write_access = {}
        self._release_RW_lock = {}
        self._release_WO_lock = {}
        for thread_name in [4, 6]:
            request_RW = _EventWithResult()
            request_WO = _EventWithResult()
            read_action = _EventWithResult()
            write_action = _EventWithResult()
            release_RW = _EventWithResult()
            release_WO = _EventWithResult()
            thread_obj = _Thread(target=self._client_thread,
                                 args=(thread_name,),
                                 name="IPv{0:d}".format(thread_name))
            self._request_RW_lock[thread_name] = request_RW
            self._request_WO_lock[thread_name] = request_WO
            self._read_access[thread_name] = read_action
            self._write_access[thread_name] = write_action
            self._release_RW_lock[thread_name] = release_RW
            self._release_WO_lock[thread_name] = release_WO
            self._client_threads[thread_name] = thread_obj
            thread_obj.start()

    def launch_test(self):
        self._test1()  # read access
        self._test2()  # write access
        self._test3()  # write access lock
        self._test4()  # request a lock whe it's owned by another.
        # TODO 5th test: non-owner release.
        # TODO 6th test: take the READ lock when WRITE is taken
        # TODO 7th test: wait until the lock expires and access
        # TODO 8th test: release the WRITE lock
        # TODO 9th test: take the READ lock and clients check the owner
        self._joiner_event.set()
        while len(self._client_threads.keys()) > 0:
            thread_key = self._client_threads.keys()[0]
            client_thread = self._client_threads.pop(thread_key)
            client_thread.join(1)
            if client_thread.is_alive():
                self._client_threads[thread_key] = client_thread

    def _test1(self, subtest=0):  # 1st test: read access
        test_name = "Clients read access"
        self._print(test_name, level=1+subtest, top=True)
        results = self._do_read_all()
        self._printResults(results)
        self._print(test_name, level=1+subtest, bottom=True)

    def _test2(self, subtest=0):  # 2nd test: write access
        test_name = "Clients write access"
        self._print(test_name, level=1+subtest, top=True)
        succeed = {}
        for thread_name in self._client_threads.keys():
            succeed[thread_name] = False
            self._write_access[thread_name].set()
            while self._write_access[thread_name].is_set():
                _sleep(1)
            read_results = self._do_read_all()
            for t_name in read_results.keys():
                self._print("Thread {0:d}: read: {1!r}"
                            "".format(t_name, read_results[t_name]), level=2)
        results = self._wait4results(self._write_access, succeed)
        self._print_results(results)
        self._print(test_name, level=1+subtest, bottom=True)

    def _test3(self):  # 3rd test: write access lock
        test_name = "One Client LOCK the WRITE access"
        self._print(test_name, level=1, top=True)
        self._request_WO_lock[4].set()
        while self._request_WO_lock[4].is_set():
            _sleep(1)
        self._print("Thread 4 should have the lock. Answer: {0!r}"
                    "".format(self._request_WO_lock[4].result), level=2)
        # self._test1(subtest=1)
        # self._test2(subtest=1)
        self._print(test_name, level=1, bottom=True)

    def _test4(self):  # 3rd test: request a lock whe it's owned by another
        test_name = "Another Client request LOCK the WRITE access "\
            "(when still is owned by another)"
        self._print(test_name, level=1, top=True)
        self._request_WO_lock[6].set()
        while self._request_WO_lock[6].is_set():
            _sleep(1)
        self._print("Thread 4 should have the lock and thread 6 NOT. "
                    "Answer: {0!r}".format(self._request_WO_lock[6].result),
                    level=2)
        # self._test1(subtest=1)
        self._print(test_name, level=1, bottom=True)

    def _do_read_all(self):
        action_done = {}
        for thread_name in self._client_threads.keys():
            action_done[thread_name] = False
            self._read_access[thread_name].set()
        return self._wait4results(self._read_access, action_done)

    def _wait4results(self, event_grp, succeed_dct):
        results = {}
        while not all(succeed_dct.values()):
            for thread_name in self._client_threads.keys():
                if succeed_dct[thread_name] is False and \
                        event_grp[thread_name].results_available():
                    result = event_grp[thread_name].result
                    # TODO: process the result to device if the test has passed
                    succeed_dct[thread_name] = True
                    results[thread_name] = result
            _sleep(0.1)
        return results

    def _client_thread(self, thread_name):
        self._print("start", level=0)
        connection_obj = self._build_client_connection(thread_name)
        while not self._joiner_event.is_set():
            self._check_action(self._request_RW_lock[thread_name],
                               'request_RW', connection_obj)
            self._check_action(self._request_WO_lock[thread_name],
                               'request_WO', connection_obj)
            # TODO: read and write
            self._check_read(thread_name, connection_obj)
            self._check_write(thread_name, connection_obj)
            self._check_action(self._release_RW_lock[thread_name],
                               'release_RW', connection_obj)
            self._check_action(self._release_WO_lock[thread_name],
                               'release_WO', connection_obj)
            _sleep(0.1)
        connection_obj.close()
        self._print("exit", level=0)

    def _build_client_connection(self, ipversion):
        if ipversion == 4:
            socket = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
            socket.connect(('127.0.0.1', 5025))
        elif ipversion == 6:
            socket = _socket.socket(_socket.AF_INET6, _socket.SOCK_STREAM)
            socket.connect(('::1', 5025))
        else:
            raise RuntimeError("Cannot build the connection to the server!")
        return socket

    def _check_action(self, event, event_tag, socket):
        if event.is_set():
            socket.send(self._commands[event_tag])
            event.result = socket.recv(1024)
            event.clear()

    def _check_read(self, thread_name, socket):
        event = self._read_access[thread_name]
        if event.is_set():
            socket.send(self._read_cmd)
            event.result = socket.recv(1024)
            event.clear()

    def _check_write(self, thread_name, socket):
        event = self._write_access[thread_name]
        if event.is_set():
            socket.send(self._write_cmd % (_randint(-100, 0), _randint(0, 100)))
            event.result = socket.recv(1024)
            event.clear()

    def _print_results(self, results):
        for thread_name in results.keys():
            self._print("Thread {0} report: {1!r}"
                        "".format(thread_name, results[thread_name]))

    def _print(self, msg, level=1, top=False, bottom=False):
        _print_info(msg, level=level, lock=self._print_lock, top=top,
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
    scpi_log2file(True)
    for test in [test_scpi]:
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
