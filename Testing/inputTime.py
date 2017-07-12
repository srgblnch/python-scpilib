from __future__ import print_function
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
#  along with this program; If not, see <http://www.gnu.org/licenses/>.
#
# ##### END GPL LICENSE BLOCK #####

__author__ = "Sergi Blanch-Torne"
__email__ = "sblanch@cells.es"
__copyright__ = "Copyright 2016, CELLS / ALBA Synchrotron"
__license__ = "GPLv3+"

try:
    from ._objects import AttrTest
except:
    from _objects import AttrTest

from datetime import datetime
from datetime import timedelta
from numpy import array
from scpilib import scpi
from scpilib.version import version as _version
from scpiObj import InstrumentIdentification
import sys
from telnetlib import Telnet
from time import sleep


def telnetRequest(tn, cmd, scpiObj):
    start_t = datetime.now()
    tn.write(cmd)
    x = tn.read_until('\n')
    t = datetime.now() - start_t - scpiObj.inputExecTime
    return t


def scpiRequest(scpiObj, cmd):
    start_t = datetime.now()
    scpiObj.input(cmd)
    return datetime.now() - start_t - scpiObj.inputExecTime


def commandTime(scpiObj, tn, cmd, tests=1, repeat=1):
    i = 0
    telnet_t = []
    input_t = []
    callback_t = []
    start_t = datetime.now()
    print("\n%d tests of command %r repeated %d times" % (tests, cmd, repeat))
    while i < tests:
        _send = (cmd+";")*repeat
        telnet_t.append(telnetRequest(tn, _send, scpiObj).total_seconds())
        diff_t = scpiObj.inputExecTime - scpiObj.callbackExecTime
        input_t.append(diff_t.total_seconds())
        callback_t.append(scpiObj.callbackExecTime.total_seconds())
        print("\Test execution: %s (%d/%d)"
              % (['|', '/', '-', '\\'][i%4], i, tests), end='\r')
        sys.stdout.flush()
        i += 1
    telnet_t = array(telnet_t)
    input_t = array(input_t)
    callback_t = array(callback_t)
    print("After %4d executions of %r (repeated %4d times) (%s)"
          "\n\t%-14s (std %-14s, max %-14s) in telnet section"
          "\n\t%-14s (std %-14s, max %-14s) inside input pre&post"
          "\n\t%-14s (std %-14s, max %-14s) inside callback"
          % (tests, cmd, repeat, datetime.now()-start_t,
             timedelta(seconds=telnet_t.mean()),
             timedelta(seconds=telnet_t.std()),
             timedelta(seconds=telnet_t.max()),
             timedelta(seconds=input_t.mean()),
             timedelta(seconds=input_t.std()),
             timedelta(seconds=input_t.max()),
             timedelta(seconds=callback_t.mean()),
             timedelta(seconds=callback_t.std()),
             timedelta(seconds=callback_t.max()),
             ))
    data = {'tests': tests,
            'subcmds': repeat,
            'cmd': cmd,
            'telnet': telnet_t,
            'input': input_t,
            'cb': callback_t}
    return data
    sleep(1)


def csv_header():
    fileName = "%s_inputTest.csv" % (datetime.now().strftime("%Y%m%d_%H%M%S"))
    with file(fileName, 'w') as f:
        f.write("#tests\t#subcmds\tcmd\ttelnet mean\ttelnet std\ttelnet max"
                "\tinput mean\tinput std\tinput max\tcb mean\tcb std\tcb max\n"
                )
    return fileName

def csv_register(fileName, data):
    with file(fileName, 'a') as f:
        f.write("%d\t%d\t%s\t" % (data['tests'], data['subcmds'], data['cmd']))
        for measure in ['telnet', 'input', 'cb']:
            t = data[measure]
            f.write("%s\t%s\t%s\t" % (t.mean(), t.std(), t.max()))
        f.write("\n")
        f.flush()


def main():
    scpiObj = scpi(name="test", local=True, debug=True, log2File=True)
    scpiObj.open()
    tn = Telnet('::1', 5025)
    identity = InstrumentIdentification('ALBA', 'test', 0, _version())
    scpiObj.addSpecialCommand('IDN', identity.idn)
    numericAttr = AttrTest()
    fileName = csv_header()
    for i in [1000]:  # number of test to extract statistical info
        for j in [10, 100]:  # how long the cmd string will be
            data = commandTime(scpiObj, tn, '*IDN?', i, j)
            csv_register(fileName, data)
            for k in range(1,6):  # how deep the tree of the command is
                cmd = ('%svalue:'%(chr(96+k))*k)[:-1]
                scpiObj.addCommand(cmd, readcb=numericAttr.readTest)
                data = commandTime(scpiObj, tn, cmd+'?', i, j)
                csv_register(fileName, data)
    tn.close()
    sleep(.1)
    scpiObj.close()


if __name__ == '__main__':
    main()
