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
__copyright__ = "Copyright 2015, CELLS / ALBA Synchrotron"
__license__ = "GPLv3+"


'''
    This file contains the necessary object to define the tree structure
    of the scpi commands. From the root to the latest nodes before the leaves
    they are Component objects that are subclass of dict. the leaves are
    an special type of components that have also the read (and the write
    optional) for the actions.
'''

try:
    from .logger import Logger as _Logger
    from .logger import timeit
except ValueError:
    from logger import Logger as _Logger
    from logger import timeit
try:
    from numpy import ndarray as _np_ndarray
    from numpy import float16 as _np_float16
    from numpy import float32 as _np_float32
    from numpy import float64 as _np_float64
    from numpy import float128 as _np_float128
    _np = True
except ValueError:
    _np = False
try:
    from scipy import ndarray as _sp_ndarray
    from scipy import float16 as _sp_float16
    from scipy import float32 as _sp_float32
    from scipy import float64 as _sp_float64
    from scipy import float128 as _sp_float128
    _sp = True
except ValueError:
    _sp = False


if _np and not _sp:
    _float16 = _np_float16
    _float32 = _np_float32
    _float64 = _np_float64
    _float128 = _np_float128
elif _sp:
    _float16 = _sp_float16
    _float32 = _sp_float32
    _float64 = _sp_float64
    _float128 = _sp_float128


MINIMUMKEYLENGHT = 4
CHNUMSIZE = 2


def getId(name, minimum):
    return sum([ord(v) << (8*i) for i, v in enumerate(name[:minimum])])


class DictKey(_Logger, str):
    '''
        This class is made to allow the dictionary keys to find a match using
        the shorter strings allowed in the scpi specs.
    '''

    __id = None
    _minimum = MINIMUMKEYLENGHT

    def __init__(self, value, *args, **kargs):
        value = str(value)
        super(DictKey, self).__init__(*args, **kargs)
        if not value.isalpha():
            raise NameError("key shall be strictly alphabetic ({0!r})"
                            "".format(value))
        self._name = value
        if 0 < len(self._name) < MINIMUMKEYLENGHT:
            self.minimum = len(value)
        if len(self._name) < self._minimum:
            raise NameError("value string shall be almost the minimum size")
        lower = self._name.lower()
        self.__id = getId(self._name.lower(), self._minimum)
        # this identifier uses only the minimum substring and depends on the
        # character positions, so an anagrama will produce a different one,
        # and it will provide a numeric way to compare keys

    def __int__(self):
        return self.__id

    @property
    def minimum(self):
        return self._minimum

    @minimum.setter
    def minimum(self, value):
        if not isinstance(value, int):
            raise TypeError("minimum shall be an integer")
        self._minimum = value

    def __str__(self):
        return self._name

    def __repr__(self):
        return "%s%s" % (self._name[0:self._minimum].upper(),
                         self._name[self._minimum:])

    # @timeit
    def __eq__(self, other):  # => self == other
        '''
            Compare if those two names matches reducing the name until the
            minimum size.
        '''
        if isinstance(other, DictKey):
            id = int(other)
        elif isinstance(other, str):
            id = getId(other, self._minimum)
        else:
            id = int(DictKey(other))
        return self.__id == id

    def __ne__(self, other):  # => self != other
        return not self == other

    def is_(self, other):  # => self is other
        return self == other

    def is_not(self, other):  # => not self is other
        return self is not other


class Attribute(DictKey):
    '''
        Leaf node of the scpi command tree
        TODO: explain property_cb difference with {read,write}_cb

        Example: COMPonent:COMPonent:ATTRibute
    '''

    _parent = None
    _read_cb = None
    _write_cb = None
    _hasChannels = False
    _channelTree = None
    _allowedArgins = None

    def __init__(self, *args, **kargs):
        super(Attribute, self).__init__(*args, **kargs)
        self._debug("Build a Attribute object {0}", self.name)

    def __str__(self):
        full_name = str(self._name)
        parent = self._parent
        while parent is not None and parent.name is not None:
            full_name = "".join("{0}:{1}".format(parent.name, full_name))
            parent = parent.parent
        return full_name

    def __repr__(self):
        # indentation = "\t"*self.depth
        return ""  # .join("\n%s%s"%(indentation,DictKey.__repr__(self)))

    @property
    def name(self):
        return self._name

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        if value is not None:
            self.logEnable(value.logState())
            self.logLevel(value.logGetLevel())
            self._parent = value

    @property
    def hasChannels(self):
        return self._hasChannels

    @property
    def allowedArgins(self):
        return self._allowedArgins

    @allowedArgins.setter
    def allowedArgins(self, value):
        # TODO: also than an specific set of values, provide a way to restrict
        #       argins in a bounded region. Like a range (or ranges) of values.
        if value is not None and type(value) is not list:
            raise TypeError("Allowed argins expects a list")
        self._allowedArgins = []
        for element in value:
            self._allowedArgins.append(str(element))
        # TODO: those strings shall also follow the key length feature
        #       if the length string is at least the minimum.
        #       This is like 'FALSe' == 'FALS' in scpi
        #       replace 'str' by 'DictKey'

    def checkChannels(self):
        if self.parent is not None and self.parent.hasChannels:
            self._hasChannels = True
            self._channelTree = self.getChannels()
            self._debug("{0}: Channels found for {1} component: {2}",
                        self.name, self.parent.name,
                        ["%s" % x.name for x in self._channelTree])
        else:
            self._debug("{0}: No channels found", self.name)

    def getChannels(self):
        if self.parent is not None and self.parent.hasChannels:
            return self.parent.getChannels()
        return None

    @property
    def read_cb(self):
        return self._read_cb

    @read_cb.setter
    def read_cb(self, function):
        self._read_cb = function

    @timeit
    def read(self, chlst=None, params=None):
        if self._read_cb is not None:
            if self.hasChannels and chlst is not None:
                if params:
                    retValue = self._callbackChannels(self._read_cb, chlst,
                                                      params)
                else:
                    retValue = self._callbackChannels(self._read_cb, chlst)
            else:
                if params:
                    retValue = self._read_cb(params)
                else:
                    retValue = self._read_cb()
                self._debug("Attribute {0} read: {1}", self.name, retValue)
            return self._check_array(retValue)

    def _check_array(self, argin):
        # if answer is a list, manipulate it to follow the rule
        # '#NMMMMMMMMM...\n'
        is_list = (type(argin) == list)
        is_np_array = None
        is_sp_array = None
        if _np:
            if is_list:
                argin = _np_ndarray(argin)
                is_list = False
            is_np_array = (type(argin) == _np_ndarray)
        if _sp:
            is_sp_array = (type(argin) == _sp_ndarray)
            if is_list:
                argin = _sp_ndarray(argin)
                is_list = False
        if is_np_array or is_sp_array:
            argout = self._convert_array(argin)
            return argout
        return argin

    def _convert_array(self, argin):
        root = self._getRootComponent()
        data_format = root['dataFormat'].read()
        # flat the array, dimensions shall be known by the receiver
        flattened = argin.flatten()
        # codification
        if data_format == 'ASCII':
            data = "".join("%s," % element for element in flattened)[:-1]
        elif data_format == 'QUADRUPLE':
            data = flattened.astype(_float128).tostring()  # + '\n'
        elif data_format == 'DOUBLE':
            data = flattened.astype(_float64).tostring()  # + '\n'
        elif data_format == 'SINGLE':
            data = flattened.astype(_float32).tostring()  # + '\n'
        elif data_format == 'HALF':
            data = flattened.astype(_float16).tostring()  # + '\n'
        # TODO: mini-precision (byte)
        # elif dataFormat == 'mini':
        #     pass
        else:
            raise NotImplementedError("Unexpected data format {0} codification"
                                      "".format(dataFormat))
        # prepare the header
        lenght = str(len(data))
        firstField = str(len(lenght))
        if len(firstField) > 1:
            self._error("A {0} array cannot be codified", lenght)
            return float("NaN")
        header = "#%1s%s" % (firstField, lenght)
        return header + data

    def _getRootComponent(self):
        candidate = self._parent
        while candidate._parent is not None:
            candidate = candidate._parent
        return candidate

    @property
    def write_cb(self):
        return self._write_cb

    @write_cb.setter
    def write_cb(self, function):
        self._write_cb = function

    @timeit
    def write(self, chlst=None, value=None):
        self._debug("{0}.write(ch={1}, value={2})", self.name, chlst, value)
        if self._write_cb is not None:
            if self.allowedArgins is not None and \
                    value not in self.allowedArgins:
                raise ValueError("Not allowed to write {0}, only {1} are "
                                 "accepted".format(value, self.allowedArgins))
            if self.hasChannels and chlst is not None:
                retValue = self._callbackChannels(self._write_cb, chlst, value)
            else:
                retValue = self._write_cb(value)
                self._debug("Attribute {0} write {1}: {2}",
                            self.name, value, retValue)
            return retValue

    def _callbackChannels(self, method_cb, chlst, value=None):
        self._checkAllChannelsAreWithinBoundaries(chlst)
        if len(chlst) == 1:
            ch = chlst[0]
            if value is None:
                retValue = method_cb(ch)
                self._debug("Attribute {0} read from channel {1:d}: {2}",
                            self.name, ch, retValue)
            else:
                retValue = method_cb(ch, value)
                self._debug("Attribute {0} write {1} in channel {2:d}: {3}",
                            self.name, value, ch, retValue)
        else:
            if value is None:
                retValue = method_cb(chlst)
                self._debug("Attribute {0} read for channel set {1}: {2}",
                            self.name, chlst, retValue)
            else:
                retValue = method_cb(chlst, value)
                self._debug("Attribute {0} write {1} for channel set {2}: {3}",
                            self.name, value, chlst, retValue)
        return retValue

    def _checkAllChannelsAreWithinBoundaries(self, chlst):
        if len(self._channelTree) != len(chlst):
            raise AssertionError("Given channel list hasn't the same number "
                                 "of elements than the known in the tree")
        for i, chRequested in enumerate(chlst):
            lowerBound = self._channelTree[i].firstChannel
            upperBound = lowerBound + self._channelTree[i].howManyChannels
            if chRequested < lowerBound:
                raise AssertionError("below the bounds")
            elif chRequested >= upperBound:
                raise AssertionError("above the bounds")


def BuildAttribute(name, parent, readcb=None, writecb=None, default=False,
                   allowedArgins=None):
    attr = Attribute(name)
    attr.parent = parent
    if parent is not None and name is not None:
        parent[name] = attr
    attr.read_cb = readcb
    attr.write_cb = writecb
    if default:
        parent.default = name
    if allowedArgins:
        attr.allowedArgins = allowedArgins
    attr.checkChannels()
    return attr


class Component(_Logger, dict):
    '''
        Intermediated nodes of the scpi command tree.

        Ex: COMPonent:COMPonent:ATTRibute
    '''

    _parent = None
    _defaultKey = None
    _howMany = None
    _hasChannels = False
    _channelTree = None
    _idxs = None

    def __init__(self, *args, **kargs):
        super(Component, self).__init__(*args, **kargs)
        self._debug("Build a Component object {0}", self.name)
        self._idxs = {}

    def __str__(self):
        full_name = str(self._name)
        parent = self._parent
        while parent is not None and parent.name is not None:
            full_name = "".join("{0}:{1}".format(parent.name, full_name))
            parent = parent.parent
        return full_name

    def __repr__(self):
        indentation = "\t"*self.depth
        repr = ""
        for key in self.keys():
            name = self._idxs[int(key)]
            item = dict.__getitem__(self, key)
            # FIXME: ugly
            if isinstance(item, Attribute):
                repr = "".join("{0}\n{1}{2!r}".format(repr, indentation, name))
            else:
                if item.default is not None:
                    isDefault = " (default {0!r}) ".format(item.default)
                else:
                    isDefault = ""
                if isinstance(item, Channel):
                    hasChannels = "NN"
                else:
                    hasChannels = ""
                repr = "".join("{0}\n{1}{2!r}{3}:{4}{5!r}"
                               "".format(repr, indentation, name, hasChannels,
                                         isDefault, item))
        return repr

    @property
    def name(self):
        return self._name

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        if value is not None:
            self.logEnable(value.logState())
            self.logLevel(value.logGetLevel())
            self._parent = value

    @property
    def default(self):
        return self._defaultKey

    @default.setter
    def default(self, value):
        if value in self.keys():
            self._defaultKey = value

    @property
    def hasChannels(self):
        return self._hasChannels

    # TODO: as any Attribute object will search for its channels in its parent
    #       component, as well as the components will search for channels also
    #       over their parents, and they are build from root to leafs:
    #       - once one finds a component with the channel feature, just copy
    #         its tree of the above channels already discovered.
    #       Right now this is following the same path over and over again.

    def checkChannels(self):
        if self.parent is not None and self.parent.hasChannels:
            self._hasChannels = True
            self._channelTree = self.getChannels()
            self._debug("{0}: Channels found for {1} component: {2}",
                        self.name, self.parent.name,
                        ["%s" % x.name for x in self._channelTree])
        else:
            self._debug("{0}: No lower level channels found", self.name)

    def getChannels(self):
        if self.parent is not None and self.parent.hasChannels:
            return self.parent.getChannels()
        return None

    # @timeit
    def __getitem__(self, key):
        '''
            Given a key, its identificator is checks if its matches with any of
            the elements in the internal structure, to then return it.
        '''
        if not isinstance(key, DictKey):
            key = DictKey(key)
        try:
            if int(key) in self._idxs.keys():
                name = self._idxs[int(key)]
                value = dict.__getitem__(self, name)
                return value
        except Exception:
            pass
        raise KeyError("{0} not found".format(key))

    def __setitem__(self, key, value):
        '''
            Key has an identificator that is used as a real key in the internal
            structure. So then any comparison is made by compare numbers.
            Also the identificator corresponds to any substring of it with
            the minimum size of 'minimumKey'
        '''
        if not isinstance(key, DictKey):
            key = DictKey(key)
        if not isinstance(value, (Component, Attribute)):
            raise ValueError("dictionary content shall be an attribute "
                             "or another Component (given {0})"
                             "".format(type(value)))
        self._idxs[int(key)] = key
        dict.__setitem__(self, key, value)
        value.parent = self

    def pop(self, key):
        if not isinstance(key, DictKey):
            key = DictKey(key)
        name = self._idxs.pop(int(key))
        value = dict.pop(self, name)
        value.parent = None
        return value

    def clear(self):
        self._idxs = {}
        dict.clear(self)

    @timeit
    def read(self, chlst=None, params=None):
        if self._defaultKey:
            return self.__getitem__(self._defaultKey).read(chlst, params)
        return float('NaN')

    @timeit
    def write(self, chlst=None, value=None):
        if self._defaultKey:
            return self.__getitem__(self._defaultKey).write(chlst, value)
        return float('NaN')


def BuildComponent(name=None, parent=None):
    component = Component(name=name)
    component.parent = parent
    if parent is not None and name is not None:
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
    def __init__(self, *args, **kargs):
        super(SpecialCommand, self).__init__(*args, **kargs)
        self._readcb = None
        self._writecb = None

    @property
    def readcb(self):
        return self._readcb

    @readcb.setter
    def readcb(self, function):
        self._readcb = function

    def read(self):
        if self._readcb is not None:
            return self._readcb()
        return float("NaN")

    @property
    def writecb(self):
        return self._writecb

    @writecb.setter
    def writecb(self, function):
        self._writecb = function

    def write(self, value=None):
        if self._writecb:
            if value:
                self._writecb(value)
            else:
                self._writecb()
        return float("NaN")


def BuildSpecialCmd(name, parent, readcb, writecb=None):
    special = SpecialCommand(name)
    special.readcb = readcb
    special.writecb = writecb
    parent[name.lower()] = special
    return special


class Channel(Component):
    def __init__(self, howMany=None, startWith=1, *args, **kargs):
        super(Channel, self).__init__(*args, **kargs)
        if len(str(howMany).zfill(2)) > CHNUMSIZE:
            raise ValueError("The number of channels can not exceed "
                             "{0:d} decimal digits".format(CHNUMSIZE))
        self._howMany = howMany
        self._startWith = startWith
        self._hasChannels = True
        self._debug("Build a Channel object {0}", self.name)

    def getChannels(self):
        if self.parent is not None and self.parent.hasChannels:
            parentChannels = self.parent.getChannels()
            if parentChannels is not None:
                return parentChannels + [self]
        return [self]

    @property
    def howManyChannels(self):
        return self._howMany

    @property
    def firstChannel(self):
        return self._startWith


def BuildChannel(name=None, howMany=None, parent=None, startWith=1):
    channel = Channel(name=name, howMany=howMany, startWith=startWith)
    channel.parent = parent
    if parent is not None and name is not None:
        parent[name] = channel
    channel.checkChannels()
    return channel
