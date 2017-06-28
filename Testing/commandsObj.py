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


try:
    from numpy.random import random as _np_randomArray
    from numpy import array as _np_array
except:
    _np_randomArray = None
from _objects import *
try:
    from ._printing import printHeader
except:
    from _printing import printHeader
from scpilib.commands import BuildAttribute
from scpilib.commands import BuildChannel
from scpilib.commands import BuildComponent
from scpilib.commands import BuildSpecialCmd
from scpilib.commands import DictKey
from scpilib.version import version


def testDictKey(output=True):
    if output:
        printHeader("Tests for the DictKey object construction")
    sampleKey = 'qwerty'
    dictKey = DictKey(sampleKey)
    if output:
        print("Compare the key and it's reduced versions")
    while dictKey == sampleKey:
        if output:
            print("\t%s == %s" % (dictKey, sampleKey))
        sampleKey = sampleKey[:-1]
    if output:
        print("\tFinally %s != %s" % (dictKey, sampleKey))
    return dictKey


def testComponent(output=True):
    # TODO: test channel like Components
    if output:
        printHeader("Tests for the Component dictionary construction")
    scpitree = BuildComponent()
    if output:
        print("Build a root component: %r" % (scpitree))
    rootNode = BuildComponent('rootnode', scpitree)
    nestedA = BuildComponent('nesteda', rootNode)
    leafA = BuildAttribute('leafa', nestedA)
    if output:
        print("Assign a nested component:%r" % (scpitree))
    nestedB = BuildComponent('nestedb', rootNode)
    leafB = BuildAttribute('leafb', nestedB)
    if output:
        print("Assign another nested component:%r" % (scpitree))
    nestedC = BuildComponent('nestedc', rootNode)
    subnestedC = BuildComponent('subnestedc', nestedC)
    leafC = BuildAttribute('leafc', subnestedC)
    if output:
        print("Assign a double nested component:%r" % (scpitree))
    return scpitree


def testAttr(output=True):
    if output:
        printHeader("Testing read/write operations construction")
    scpitree = BuildComponent()
    voltageObj = AttrTest()
    currentObj = AttrTest()
    source = BuildComponent('source', scpitree)
    voltageComp = BuildComponent('voltage', source)
    UpperVoltage = BuildAttribute('upper', voltageComp,
                                  readcb=voltageObj.upperLimit,
                                  writecb=voltageObj.upperLimit)
    LowerVoltage = BuildAttribute('lower', voltageComp,
                                  readcb=voltageObj.lowerLimit,
                                  writecb=voltageObj.lowerLimit)
    ReadVoltage = BuildAttribute('value', voltageComp,
                                 readcb=voltageObj.readTest,
                                 default=True)
    currentComp = BuildComponent('current', source)
    UpperCurrent = BuildAttribute('upper', currentComp,
                                  readcb=currentObj.upperLimit,
                                  writecb=currentObj.upperLimit)
    LowerCurrent = BuildAttribute('lower', currentComp,
                                  readcb=currentObj.lowerLimit,
                                  writecb=currentObj.lowerLimit)
    ReadCurrent = BuildAttribute('value', currentComp,
                                 readcb=currentObj.readTest,
                                 default=True)
    if output:
        print("%r" % (scpitree))
    return scpitree


def idn():
    return "ALBA,test,0,%s" % (version())


def testSpeciaCommands(output=True):
    if output:
        printHeader("Testing the special commands construction")
    scpiSpecials = BuildComponent()
    idnCmd = BuildSpecialCmd("IDN", scpiSpecials, idn)
    if output:
        print("IDN answer: %s" % (scpiSpecials["IDN"].read()))
    return scpiSpecials


def testChannels(output=True):
    if output:
        printHeader("Testing the channels commands construction")
    scpiChannels = BuildComponent()
    voltageObj = ChannelTest(nChannels)
    currentObj = ChannelTest(nChannels)
    channels = BuildChannel("channel", nChannels, scpiChannels)
    voltageComp = BuildComponent('voltage', channels)
    UpperVoltage = BuildAttribute('upper', voltageComp,
                                  readcb=voltageObj.upperLimit,
                                  writecb=voltageObj.upperLimit)
    LowerVoltage = BuildAttribute('lower', voltageComp,
                                  readcb=voltageObj.lowerLimit,
                                  writecb=voltageObj.lowerLimit)
    ReadVoltage = BuildAttribute('value', voltageComp,
                                 readcb=voltageObj.readTest,
                                 default=True)
    currentComp = BuildComponent('current', channels)
    UpperCurrent = BuildAttribute('upper', currentComp,
                                  readcb=currentObj.upperLimit,
                                  writecb=currentObj.upperLimit)
    LowerCurrent = BuildAttribute('lower', currentComp,
                                  readcb=currentObj.lowerLimit,
                                  writecb=currentObj.lowerLimit)
    ReadCurrent = BuildAttribute('value', currentComp,
                                 readcb=currentObj.readTest,
                                 default=True)
    if output:
        print("%r" % (scpiChannels))
    return scpiChannels


def testChannelsWithSubchannels(output=True):
    if output:
        printHeader("Testing the nested channels commands construction")
    scpiChannels = BuildComponent()
    voltageObj = SubchannelTest(nChannels, nSubchannels)
    currentObj = SubchannelTest(nChannels, nSubchannels)
    channels = BuildChannel("channel", nChannels, scpiChannels)
    measures = BuildComponent('measures', channels)
    functions = BuildChannel("function", nSubchannels, measures)
    voltageComp = BuildComponent('voltage', functions)
    UpperVoltage = BuildAttribute('upper', voltageComp,
                                  readcb=voltageObj.upperLimit,
                                  writecb=voltageObj.upperLimit)
    LowerVoltage = BuildAttribute('lower', voltageComp,
                                  readcb=voltageObj.lowerLimit,
                                  writecb=voltageObj.lowerLimit)
    ReadVoltage = BuildAttribute('value', voltageComp,
                                 readcb=voltageObj.readTest,
                                 default=True)
    currentComp = BuildComponent('current', functions)
    UpperCurrent = BuildAttribute('upper', currentComp,
                                  readcb=currentObj.upperLimit,
                                  writecb=currentObj.upperLimit)
    LowerCurrent = BuildAttribute('lower', currentComp,
                                  readcb=currentObj.lowerLimit,
                                  writecb=currentObj.lowerLimit)
    ReadCurrent = BuildAttribute('value', currentComp,
                                 readcb=currentObj.readTest,
                                 default=True)
    if output:
        print("%r" % (scpiChannels))
    return scpiChannels


def testArrayAnswers(output=True):
    if output:
        printHeader("Testing the array conversion answers")
    scpiArrays = BuildComponent()
    reading = ArrayTest()
    arrayreader = BuildAttribute('readarray', scpiArrays,
                                 readcb=reading.readTest)
    if output:
        print("%r" % (scpiArrays))
    return scpiArrays


def main():
    import traceback
    for test in [testDictKey, testComponent, testAttr, testSpeciaCommands,
                 testChannels, testChannelsWithSubchannels, testArrayAnswers]:
        try:
            test()
        except Exception as e:
            print("Test failed! %s" % (e))
            traceback.print_exc()
            return


if __name__ == '__main__':
    main()
