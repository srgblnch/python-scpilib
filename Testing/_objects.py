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

__author__ = "Sergi Blanch-Torne"
__email__ = "sblanch@cells.es"
__copyright__ = "Copyright 2016, CELLS / ALBA Synchrotron"
__license__ = "GPLv3+"


from random import randint
from scpi.commands import _np, _float16, _float32, _float64, _float128

try:
    from numpy.random import random as _np_randomArray
    from numpy import array as _np_array
except:
    _np_randomArray = None


nChannels = 8
nSubchannels = nChannels*2


class AttrTest:
    def __init__(self, upperLimit=100, lowerLimit=-100):
        self._upperLimit = upperLimit
        self._lowerLimit = lowerLimit

    def readTest(self):
        return randint(self._lowerLimit, self._upperLimit)

    def upperLimit(self, value=None):
        if value is None:
            return self._upperLimit
        self._upperLimit = float(value)

    def lowerLimit(self, value=None):
        if value is None:
            return self._lowerLimit
        self._lowerLimit = float(value)

    def exceptionTest(self):
        raise Exception("controlled exception")


class WattrTest(AttrTest):
    def __init__(self, upperLimit=100, lowerLimit=-100):
        AttrTest.__init__(self, upperLimit, lowerLimit)
        self._value = randint(self._lowerLimit, self._upperLimit)
        self._switch = False

    def readTest(self):
        #print("read %s" % self._value)
        return self._value

    def writeTest(self, value):
        #print("write %s" % value)
        self._value = value

    def switchTest(self):
        self._switch = not self._switch
        return self._switch


class ChannelTest:
    def __init__(self, channels=4, upperLimit=100, lowerLimit=-100):
        self._upperLimit = [upperLimit]*channels
        self._lowerLimit = [lowerLimit]*channels
        # channels starts from 1 and list indexes from 0

    def readTest(self, ch):
        return randint(self._lowerLimit[ch-1], self._upperLimit[ch-1])

    def upperLimit(self, ch, value=None):
        if value is None:
            return self._upperLimit[ch-1]
        self._upperLimit[ch-1] = float(value)

    def lowerLimit(self, ch, value=None):
        if value is None:
            return self._lowerLimit[ch-1]
        self._lowerLimit[ch-1] = float(value)


class WchannelTest(ChannelTest):
    def __init__(self, channels=4, upperLimit=100, lowerLimit=-100):
        ChannelTest.__init__(self, channels, upperLimit, lowerLimit)
        self._value = []
        for i in range(channels):
            lowerLimit = self._lowerLimit[i]
            upperLimit = self._upperLimit[i]
            self._value.append(randint(lowerLimit, upperLimit))

    def readTest(self, ch):
        return self._value[ch-1]

    def writeTest(self, ch, value):
        self._value[ch-1] = value


class SubchannelTest:
    def __init__(self, channels=4, subchannels=8,
                 upperLimit=100, lowerLimit=-100):
        self._upperLimit = [[upperLimit]*subchannels]*channels
        self._lowerLimit = [[lowerLimit]*subchannels]*channels
        # channels starts from 1 and list indexes from 0

    def readTest(self, chlst):
        ch, subch = chlst
        return randint(self._lowerLimit[ch-1][subch-1],
                       self._upperLimit[ch-1][subch-1])

    def upperLimit(self, chlst, value=None):
        ch, subch = chlst
        if value is None:
            return self._upperLimit[ch-1][subch-1]
        self._upperLimit[ch-1][subch-1] = float(value)

    def lowerLimit(self, chlst, value=None):
        ch, subch = chlst
        if value is None:
            return self._lowerLimit[ch-1][subch-1]
        self._lowerLimit[ch-1][subch-1] = float(value)


class ArrayTest:
    def __init__(self, length=100):
        self._length = length

    def readTest(self):
        if _np and _np_randomArray is not None:
            multiplier = 1/_float128(_np_randomArray())
            shifter = 1/_float128(_np_randomArray())
            elements = _np_randomArray(self._length).astype(_float128)
            return (multiplier * elements) + shifter
        else:
            lst = []
            for i in range(self._length):
                lst.append(random())
            return lst

    def readRange(self, params):
        start, end = params.split(',')
        start = int(start)
        end = int(end)
        answer = range(start, end+1)
        if _np and _np_array:
            answer = _np_array(answer)
        return answer
