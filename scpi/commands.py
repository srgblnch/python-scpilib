###############################################################################
## file :               commands.py
##
## description :        Python module to provide scpi functionality to an 
##                      instrument.
##
## project :            scpi
##
## author(s) :          S.Blanch-Torn\'e
##
## Copyright (C) :      2015
##                      CELLS / ALBA Synchrotron,
##                      08290 Bellaterra,
##                      Spain
##
## This file is part of Tango.
##
## Tango is free software: you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## Tango is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Tango.  If not, see <http:##www.gnu.org/licenses/>.
##
###############################################################################


'''
    This file contains the necessary object to define the tree structure 
    of the scpi commands. From the root to the latest nodes before the leaves 
    they are Component objects that are subclass of dict. the leaves are
    an special type of components that have also the read (and the write 
    optional) for the actions.
'''

try:
    from .logger import Logger as _Logger
except:
    from logger import Logger as _Logger

MINIMUMKEYLENGHT = 4

class DictKey(_Logger,str):
    '''
        This class is made to allow the dictionary keys to find a match using 
        the shorter strings allowed in the scpi specs.
    '''
    def __init__(self, value, *args, **kargs):
        super(DictKey,self).__init__(*args, **kargs)
        if not value.isalpha():
            raise NameError("key shall be strictly alphabetic")
        self._name = value
        if 0 < len(self._name) < MINIMUMKEYLENGHT:
            self.minimum = len(value)
        else:
            self.minimum = MINIMUMKEYLENGHT
        if len(self._name) < self.minimum:
            raise NameError("value string shall be almost "
                            "the minimum size")
    
    @property
    def minimum(self):
        return self._minimum
    
    @minimum.setter
    def minimum(self,value):
        if type(value) != int:
            raise TypeError("minimum shall be an integer")
        self._minimum = value
    
    def __str__(self):
        return self._name
        
    def __repr__(self):
        return "%s%s"%(self._name[0:self._minimum].upper(),
                       self._name[self._minimum:])
    
    def __eq__(self,other):# => self == other
        '''
            Compare if those two names matches reducing the name until the 
            minimum size.
        '''
        if type(other) == DictKey:
            otherName = other._name.lower()
        elif type(other) == str:
            otherName = other.lower()
        else:
            otherName = ''
        selfName = self._name.lower()
        self._debug("Comparing %s to %s"%(selfName,otherName))
        while len(selfName) >= len(otherName) and \
        len(selfName) >= self._minimum:
            if selfName == otherName:
                self._debug("Found match! %s == %s"%(selfName,otherName))
                return True
            if len(selfName) > self._minimum:
                self._debug("No match found, reducing %s to %s"
                           %(selfName,selfName[:-1]))
            selfName = selfName[:-1]
        return False
    
    def is_(self,other):# => self is other
        return self == other
    
    def __ne__(self,other):# => self != other
        return not self == other
    
    def is_not(self,other):# => not self is other
        return not self is other


class Attribute(DictKey):
    '''
        Leaf node of the scpi command tree
        TODO: explain property_cb difference with {read,write}_cb
        
        Example: COMPonent:COMPonent:ATTRibute
    '''
    def __init__(self,*args,**kargs):
        super(Attribute,self).__init__(*args,**kargs)
        self._parent = None
        self._read_cb = None
        self._write_cb = None
        self._hasChannels = False

    def __str__(self):
        repr = "%s"%(self._name)
        parent = self._parent
        while parent != None and parent._name != None:
            repr = "".join("%s:%s"%(parent._name,repr))
            parent = parent._parent
        return repr

    def __repr__(self):
        indentation = "\t"*self.depth
        return ""#.join("\n%s%s"%(indentation,DictKey.__repr__(self)))

    @property
    def name(self):
        return self._name

    @property
    def parent(self):
        return self._parent
    
    @parent.setter
    def parent(self,value):
        self._parent = value

    @property
    def hasChannels(self):
        return self._hasChannels

    def checkChannels(self):
        parent = self.parent
        while parent != None:
            if parent.hasChannels:
                self._hasChannels = True
                self._info("%s: Channels found for %s component"
                           % (self.name,parent.name))
                return
            parent = parent.parent  # next
        self._info("%s: No channels found" % (self.name))

    @property
    def read_cb(self):
        return self._read_cb
    
    @read_cb.setter
    def read_cb(self,function):
        self._read_cb = function

    def read(self):
        return self._read_cb()
    
    @property
    def write_cb(self):
        return self._write_cb
    
    @write_cb.setter
    def write_cb(self,function):
        self._write_cb = function

    def write(self,value):
        self._write_cb(value)


def BuildAttribute(name,parent,readcb=None,writecb=None,default=False):
    attr = Attribute(name)
    attr.parent = parent
    if parent != None:
        parent[name] = attr
    attr.read_cb = readcb
    attr.write_cb = writecb
    if default:
        parent.default = name
    attr.checkChannels()
    return attr


class Component(_Logger,dict):
    '''
        Intermediated nodes of the scpi command tree.
        
        Ex: COMPonent:COMPonent:ATTRibute
    '''
    def __init__(self, *args, **kargs):
        super(Component,self).__init__(*args, **kargs)
        self._parent = None
        self._defaultKey = None
        self._howMany = None
        self._hasChannels = False

    def __str__(self):
        repr = "%s"%(self._name)
        parent = self._parent
        while parent != None and parent._name != None:
            repr = "".join("%s:%s"%(parent._name,repr))
            parent = parent._parent
        return repr

    def __repr__(self):
        indentation = "\t"*self.depth
        repr = ""
        for key in self.keys():
            item = dict.__getitem__(self, key)
            #FIXME: ugly
            if isinstance(item,Attribute):
                repr = "".join("%s\n%s%r"%(repr,indentation,key))
            else:
                if item.default != None:
                    isDefault = " (default %s) " % item.default
                else:
                    isDefault = ""
                if isinstance(item,Channel):
                    hasChannels = "NN"
                else:
                    hasChannels = ""
                repr = "".join("%s\n%s%r%s:%s%r"
                               % (repr, indentation, key, hasChannels,
                                  isDefault, item))
        return repr

    @property
    def name(self):
        return self._name

    @property
    def parent(self):
        return self._parent
    
    @parent.setter
    def parent(self,value):
        self._parent = value

    @property
    def hasChannels(self):
        return self._hasChannels
    
    @property
    def isChanneled(self):
        itis = self._howMany is not None
        self._info("isChanneled = %s" % itis)
        return itis

    def checkChannels(self):
        parent = self.parent
        while parent != None:
            if parent.hasChannels:
                self._hasChannels = True
                self._info("%s: Channels found for %s component"
                           % (self.name,parent.name))
                return
            parent = parent.parent  # next
        self._info("%s: No channels found" % (self.name))

    def __getitem__(self, key):
        '''
            Given a keyword it checks if it matches, at least the first 
            'minimumkey' characters, with an key in the dictionary to return 
            its content.
        '''
        self._debug("available keywords: %s"%(self.keys()))
        for keyword in self.keys():
            if keyword == key:
                key = keyword
                break
        try:
            val = dict.__getitem__(self, key)
        except:
            raise KeyError("%s not found"%(key))
        self._debug("GET %s['%r'] = %s"
                  %(str(dict.get(self,'name_label')),key,str(val)))
        return val
    
    def __setitem__(self, key, val):
        '''
            The key is case insensitive, then we store it as lower case to
            compare every where lower cases. Also the key corresponds to any
            substring of it with the minimum size of 'minimumKey'
        '''
        if type(key) != DictKey:
            key = DictKey(key)
        if not isinstance(val, (Component, Attribute)):
            raise ValueError("dictionary content shall be an attribute "
                             "or another Component (given %s)" % type(val))
        self._debug("SET %s['%r'] = %s"
                   % (str(dict.get(self, 'name_label')), key, str(val)))
        dict.__setitem__(self, key, val)
        val.parent = self

    @property
    def default(self):
        return self._defaultKey
    
    @default.setter
    def default(self,value):
        if value in self.keys():
            self._defaultKey = value

    def read(self):
        if self._defaultKey:
            return self.__getitem__(self._defaultKey).read()
        return float('NaN')
    
    def write(self,value):
        if self._defaultKey:
            return self.__getitem__(self._defaultKey).write(value)
        return float('NaN')


def BuildComponent(name=None,parent=None):
    component = Component(name=name)
    component.parent = parent
    if parent != None and name != None:
        parent[name] = component
    component.checkChannels()
    return component


class SpecialCommand(Component):
    '''
        Special commands that starts with '*' character. To be know, the 
        mandatory commands that must have an instrument that provice scpi
        communications are:
        *IDN?: Identification query
                four field response: 
                "MANUFACTURER,INSTRUMENT,SERIALNUMBER,FIRMWARE_VERSION
                    Manufacturer: identical for all the instruments of a 
                                  single company
                    Instrument: It shall never contain the word 'MODEL'.
                    SN: specific for the responding instrument
                    version (and revision): of the software embedded in the 
                                            instrument.
        *RST: Reset command
        *CLS: Clear status command
        *ESE[?]: Event Status Enable
        *ESR?: Event Status Register query
        *OPC[?]: Operation Complete
        *SRE[?]: Service Request Enable
        *STB?: Status Byte
        *TST?: self-test query
        *WAI: wait-to-continue command
    '''
    def __init__(self,*args,**kargs):
        super(SpecialCommand,self).__init__(*args,**kargs)
        self._readcb = None
        self._writecb = None
        
    @property
    def readcb(self):
        return self._readcb
    
    @readcb.setter
    def readcb(self,function):
        self._readcb = function
        
    def read(self):
        if self._readcb != None:
            return self._readcb()
        return float("NaN")
    
    @property
    def writecb(self):
        return self._writecb
    
    @writecb.setter
    def writecb(self,function):
        self._writecb = function
    
    def write(self,value=None):
        if self._writecb:
            if value:
                self._writecb(value)
            else:
                self._writecb()
        return float("NaN")


def BuildSpecialCmd(name,parent,readcb,writecb=None):
    special = SpecialCommand(name)
    special.readcb = readcb
    special.writecb = writecb
    parent[name.lower()] = special
    return special


class Channel(Component):
    def __init__(self,howMany=None,*args,**kargs):
        super(Channel,self).__init__(*args,**kargs)
        self._howMany = howMany
        self._hasChannels = True


def BuildChannel(name=None,howMany=None,parent=None):
    channel = Channel(name=name,howMany=howMany)
    channel.parent = parent
    if parent != None and name != None:
        parent[name] = channel
    return channel


#---- TEST AREA
try:
    from .logger import printHeader
except:
    from logger import printHeader
from random import randint


def testDictKey(output=True):
    if output:
        printHeader("Tests for the DictKey object construction")
    sampleKey = 'qwerty'
    dictKey = DictKey(sampleKey)
    if output:
        print("Compare the key and it's reduced versions")
    while dictKey == sampleKey:
        if output:
            print("\t%s == %s"%(dictKey,sampleKey))
        sampleKey = sampleKey[:-1]
    if output:
        print("\tFinally %s != %s"%(dictKey,sampleKey))
    return dictKey


def testComponent(output=True):
    #TODO: test channel like Components
    if output:
        printHeader("Tests for the Component dictionary construction")
    scpitree = BuildComponent()
    if output:
        print("Build a root component: %r"%(scpitree))
    rootNode = BuildComponent('rootnode',scpitree)
    nestedA = BuildComponent('nesteda',rootNode)
    leafA = BuildAttribute('leafa',nestedA)
    if output:
        print("Assign a nested component:%r"%(scpitree))
    nestedB = BuildComponent('nestedb',rootNode)
    leafB = BuildAttribute('leafb',nestedB)
    if output:
        print("Assign another nested component:%r"%(scpitree))
    nestedC = BuildComponent('nestedc',rootNode)
    subnestedC = BuildComponent('subnestedc',nestedC)
    leafC = BuildAttribute('leafc',subnestedC)
    if output:
        print("Assign a double nested component:%r"%(scpitree))
    return scpitree


class AttrTest:
    def __init__(self,upperLimit=100,lowerLimit=-100):
        self._upperLimit = upperLimit
        self._lowerLimit = lowerLimit
    def readTest(self):
        return randint(self._lowerLimit,self._upperLimit)
    def upperLimit(self,value=None):
        if value == None:
            return self._upperLimit
        self._upperLimit = float(value)
    def lowerLimit(self,value=None):
        if value == None:
            return self._lowerLimit
        self._lowerLimit = float(value)


def testAttr(output=True):
    if output:
        printHeader("Testing read/write operations construction")
    scpitree = BuildComponent()
    voltageObj = AttrTest()
    currentObj = AttrTest()
    source = BuildComponent('source',scpitree)
    voltageComp = BuildComponent('voltage',source)
    UpperVoltage = BuildAttribute('upper',voltageComp,
                                  readcb=voltageObj.upperLimit,
                                  writecb=voltageObj.upperLimit)
    LowerVoltage = BuildAttribute('lower',voltageComp,
                                  readcb=voltageObj.lowerLimit,
                                  writecb=voltageObj.lowerLimit)
    ReadVoltage = BuildAttribute('value',voltageComp,
                                  readcb=voltageObj.readTest,
                                  default=True)
    currentComp = BuildComponent('current',source)
    UpperCurrent = BuildAttribute('upper',currentComp,
                                  readcb=currentObj.upperLimit,
                                  writecb=currentObj.upperLimit)
    LowerCurrent = BuildAttribute('lower',currentComp,
                                  readcb=currentObj.lowerLimit,
                                  writecb=currentObj.lowerLimit)
    ReadCurrent = BuildAttribute('value',currentComp,
                                  readcb=currentObj.readTest,
                                  default=True)
    if output:
        print("%r"%scpitree)
    return scpitree


def idn():
    return "ALBA,test,0,0.0"


def testSpeciaCommands(output=True):
    if output:
        printHeader("Testing the special commands construction")
    scpiSpecials = BuildComponent()
    idnCmd = BuildSpecialCmd("IDN",scpiSpecials,idn)
    if output:
        print("IDN answer: %s"%(scpiSpecials["IDN"].read()))
    return scpiSpecials


class ChannelTest:
    def __init__(self,channels=4,upperLimit=100,lowerLimit=-100):
        self._upperLimit = [upperLimit]*channels
        self._lowerLimit = [lowerLimit]*channels
    def readTest(self,ch):
        return randint(self._lowerLimit[ch],self._upperLimit[ch])
    def upperLimit(self,ch,value=None):
        if value == None:
            return self._upperLimit[ch]
        self._upperLimit[ch] = float(value)
    def lowerLimit(self,ch,value=None):
        if value == None:
            return self._lowerLimit[ch]
        self._lowerLimit[ch] = float(value)


def testChannels(output=True):
    if output:
        printHeader("Testing the channels commands construction")
    scpiChannels = BuildComponent()
    voltageObj = ChannelTest()
    currentObj = ChannelTest()
    channels = BuildChannel("channel",4,scpiChannels)
    voltageComp = BuildComponent('voltage',channels)
    UpperVoltage = BuildAttribute('upper',voltageComp,
                                  readcb=voltageObj.upperLimit,
                                  writecb=voltageObj.upperLimit)
    LowerVoltage = BuildAttribute('lower',voltageComp,
                                  readcb=voltageObj.lowerLimit,
                                  writecb=voltageObj.lowerLimit)
    ReadVoltage = BuildAttribute('value',voltageComp,
                                  readcb=voltageObj.readTest,
                                  default=True)
    currentComp = BuildComponent('current',channels)
    UpperCurrent = BuildAttribute('upper',currentComp,
                                  readcb=currentObj.upperLimit,
                                  writecb=currentObj.upperLimit)
    LowerCurrent = BuildAttribute('lower',currentComp,
                                  readcb=currentObj.lowerLimit,
                                  writecb=currentObj.lowerLimit)
    ReadCurrent = BuildAttribute('value',currentComp,
                                  readcb=currentObj.readTest,
                                  default=True)
    if output:
        print("%r"%scpiChannels)
    return scpiChannels


def main():
    import traceback
    for test in [testDictKey, testComponent, testAttr, testSpeciaCommands,
                 testChannels]:
        try:
            test()
        except Exception as e:
            print("Test failed! %s"%e)
            traceback.print_exc()
            return


if __name__ == '__main__':
    main()