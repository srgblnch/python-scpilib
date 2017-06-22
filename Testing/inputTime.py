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
from scpi import scpi
from scpi.version import version as _version
from scpiObj import InstrumentIdentification


def commandTime(scpiObj, cmd, tests=1, cmdRepeat=1):
    i = 0
    total_t = []
    callback_t = []
    start_t = datetime.now()
    while i < tests:
        scpiObj.input((cmd+";")*cmdRepeat)
        total_t.append(scpiObj.inputExecTime.total_seconds())
        callback_t.append(scpiObj.callbackExecTime.total_seconds())
        #scpiObj.callbackExecList
        i += 1
    total_t = array(total_t)
    callback_t = array(callback_t)
    print("\nAfter %4d executions of %r (repeated %4d times) (%s)"
          "\n\t%-14s (std %-14s) total call"
          "\n\t%-14s (std %-14s) in callback\n"
          % (tests, cmd, cmdRepeat, datetime.now()-start_t,
             timedelta(seconds=total_t.mean()),
             timedelta(seconds=total_t.std()),
             timedelta(seconds=callback_t.mean()),
             timedelta(seconds=callback_t.std())))


def main():
    scpiObj = scpi(local=True, debug=True, log2File=True)
    scpiObj.open()
    identity = InstrumentIdentification('ALBA', 'test', 0, _version())
    scpiObj.addSpecialCommand('IDN', identity.idn)
    for j in [1, 10, 100]:
        for i in [1000]:
            commandTime(scpiObj, '*IDN?', i, j)
    numericAttr = AttrTest()
    scpiObj.addCommand('value', readcb=numericAttr.readTest)
    for j in [1, 10, 100]:
        for i in [1000]:
            commandTime(scpiObj, 'value?', i, j)
    


if __name__ == '__main__':
    main()
