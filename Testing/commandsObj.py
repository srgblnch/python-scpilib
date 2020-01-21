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
except Exception:
    _np_randomArray = None
from _objects import *
from _printing import printHeader
from scpilib.commands import build_attribute
from scpilib.commands import build_channel
from scpilib.commands import build_component
from scpilib.commands import build_special_cmd
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
    scpitree = build_component()
    if output:
        print("Build a root component: %r" % (scpitree))
    rootNode = build_component('rootnode', scpitree)
    nestedA = build_component('nesteda', rootNode)
    leafA = build_attribute('leafa', nestedA)
    if output:
        print("Assign a nested component:%r" % (scpitree))
    nestedB = build_component('nestedb', rootNode)
    leafB = build_attribute('leafb', nestedB)
    if output:
        print("Assign another nested component:%r" % (scpitree))
    nestedC = build_component('nestedc', rootNode)
    subnestedC = build_component('subnestedc', nestedC)
    leafC = build_attribute('leafc', subnestedC)
    if output:
        print("Assign a double nested component:%r" % (scpitree))
    return scpitree


def testAttr(output=True):
    if output:
        printHeader("Testing read/write operations construction")
    scpitree = build_component()
    voltageObj = AttrTest()
    currentObj = AttrTest()
    source = build_component('source', scpitree)
    voltageComp = build_component('voltage', source)
    UpperVoltage = build_attribute('upper', voltageComp,
                                   read_cb=voltageObj.upperLimit,
                                   write_cb=voltageObj.upperLimit)
    LowerVoltage = build_attribute('lower', voltageComp,
                                   read_cb=voltageObj.lowerLimit,
                                   write_cb=voltageObj.lowerLimit)
    ReadVoltage = build_attribute('value', voltageComp,
                                  read_cb=voltageObj.readTest,
                                  default=True)
    currentComp = build_component('current', source)
    UpperCurrent = build_attribute('upper', currentComp,
                                   read_cb=currentObj.upperLimit,
                                   write_cb=currentObj.upperLimit)
    LowerCurrent = build_attribute('lower', currentComp,
                                   read_cb=currentObj.lowerLimit,
                                   write_cb=currentObj.lowerLimit)
    ReadCurrent = build_attribute('value', currentComp,
                                  read_cb=currentObj.readTest,
                                  default=True)
    if output:
        print("%r" % (scpitree))
    return scpitree


def idn():
    return "ALBA,test,0,%s" % (version())


def testSpeciaCommands(output=True):
    if output:
        printHeader("Testing the special commands construction")
    scpiSpecials = build_component()
    idnCmd = build_special_cmd("IDN", scpiSpecials, idn)
    if output:
        print("IDN answer: %s" % (scpiSpecials["IDN"].read()))
    return scpiSpecials


def testChannels(output=True):
    if output:
        printHeader("Testing the channels commands construction")
    scpiChannels = build_component()
    voltageObj = ChannelTest(nChannels)
    currentObj = ChannelTest(nChannels)
    channels = build_channel("channel", nChannels, scpiChannels)
    voltageComp = build_component('voltage', channels)
    UpperVoltage = build_attribute('upper', voltageComp,
                                   read_cb=voltageObj.upperLimit,
                                   write_cb=voltageObj.upperLimit)
    LowerVoltage = build_attribute('lower', voltageComp,
                                   read_cb=voltageObj.lowerLimit,
                                   write_cb=voltageObj.lowerLimit)
    ReadVoltage = build_attribute('value', voltageComp,
                                  read_cb=voltageObj.readTest,
                                  default=True)
    currentComp = build_component('current', channels)
    UpperCurrent = build_attribute('upper', currentComp,
                                   read_cb=currentObj.upperLimit,
                                   write_cb=currentObj.upperLimit)
    LowerCurrent = build_attribute('lower', currentComp,
                                   read_cb=currentObj.lowerLimit,
                                   write_cb=currentObj.lowerLimit)
    ReadCurrent = build_attribute('value', currentComp,
                                  read_cb=currentObj.readTest,
                                  default=True)
    if output:
        print("%r" % (scpiChannels))
    return scpiChannels


def testChannelsWithSubchannels(output=True):
    if output:
        printHeader("Testing the nested channels commands construction")
    scpiChannels = build_component()
    voltageObj = SubchannelTest(nChannels, nSubchannels)
    currentObj = SubchannelTest(nChannels, nSubchannels)
    channels = build_channel("channel", nChannels, scpiChannels)
    measures = build_component('measures', channels)
    functions = build_channel("function", nSubchannels, measures)
    voltageComp = build_component('voltage', functions)
    UpperVoltage = build_attribute('upper', voltageComp,
                                   read_cb=voltageObj.upperLimit,
                                   write_cb=voltageObj.upperLimit)
    LowerVoltage = build_attribute('lower', voltageComp,
                                   read_cb=voltageObj.lowerLimit,
                                   write_cb=voltageObj.lowerLimit)
    ReadVoltage = build_attribute('value', voltageComp,
                                  read_cb=voltageObj.readTest,
                                  default=True)
    currentComp = build_component('current', functions)
    UpperCurrent = build_attribute('upper', currentComp,
                                   read_cb=currentObj.upperLimit,
                                   write_cb=currentObj.upperLimit)
    LowerCurrent = build_attribute('lower', currentComp,
                                   read_cb=currentObj.lowerLimit,
                                   write_cb=currentObj.lowerLimit)
    ReadCurrent = build_attribute('value', currentComp,
                                  read_cb=currentObj.readTest,
                                  default=True)
    if output:
        print("%r" % (scpiChannels))
    return scpiChannels


def testArrayAnswers(output=True):
    if output:
        printHeader("Testing the array conversion answers")
    scpiArrays = build_component()
    reading = ArrayTest()
    arrayreader = build_attribute('readarray', scpiArrays,
                                  read_cb=reading.readTest)
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
