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
    from .logger import deprecated, deprecated_argument
except Exception:
    from logger import Logger as _Logger
    from logger import timeit
    from logger import deprecated, deprecated_argument
try:
    from numpy import ndarray as _np_ndarray
    from numpy import float16 as _np_float16
    from numpy import float32 as _np_float32
    from numpy import float64 as _np_float64
    from numpy import float128 as _np_float128
    _np = True
except Exception:
    _np = False
try:
    from scipy import ndarray as _sp_ndarray
    from scipy import float16 as _sp_float16
    from scipy import float32 as _sp_float32
    from scipy import float64 as _sp_float64
    from scipy import float128 as _sp_float128
    _sp = True
except Exception:
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


def get_id(name, minimum):
    """
Converts an string to a reproducible numeric number. Strings that starts with
the same minimum value will collide with the same code.

It is case insensitive:
hex(get_id("Start", 4))
 '0x73746172'
hex(get_id("STARt", 4))
 '0x73746172'

Two words have different code:
hex(get_id("Stop", 4))
 '0x73746f70'

Only if the minimum doesn't force a collision:
hex(get_id("Stop", 2))
 '0x7374'
hex(get_id("Start", 2))
 '0x7374'
hex(get_id("INETfour", 4))
 '0x696e6574'
hex(get_id("INETsix", 4))
 '0x696e6574'
    """
    return sum([ord(v) << (8*(minimum-i-1))
                for i, v in enumerate(name.lower()[:minimum])])


@deprecated
def getId(*args, **kwargs):
    return get_id(*args, **kwargs)


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
        self.__id = get_id(self._name.lower(), self._minimum)
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
            id = get_id(other, self._minimum)
        else:
            id = int(DictKey(other))
        # self._debug("({1}) compare with '{2}' ({3})"
        #             "".format(self, hex(self.__id), other, hex(id)))
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
    _has_channels = False
    _channel_tree = None
    _allowed_argins = None

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
    def has_channels(self):
        return self._has_channels

    @property
    @deprecated
    def hasChannels(self):
        return self.has_channels

    @property
    @deprecated
    def _hasChannels(self):
        return self._has_channels

    @property
    def allowed_argins(self):
        return self._allowed_argins

    @property
    @deprecated
    def allowedArgins(self):
        return self.allowed_argins

    @property
    @deprecated
    def _allowedArgins(self):
        return self._allowed_argins

    @allowed_argins.setter
    def allowed_argins(self, value):
        # TODO: also than an specific set of values, provide a way to restrict
        #       argins in a bounded region. Like a range (or ranges) of values.
        if value is not None and type(value) is not list:
            raise TypeError("Allowed argins expects a list")
        self._allowed_argins = []
        for element in value:
            self._allowed_argins.append(str(element))
        # TODO: those strings shall also follow the key length feature
        #       if the length string is at least the minimum.
        #       This is like 'FALSe' == 'FALS' in scpi
        #       replace 'str' by 'DictKey'

    @allowedArgins.setter
    @deprecated
    def allowedArgins(self, value):
        self.allowed_argins = value

    @_allowedArgins.setter
    @deprecated
    def _allowedArgins(self, value):
        self._allowed_argins = value

    def check_channels(self):
        if self.parent is not None and self.parent.has_channels:
            self._has_channels = True
            self._channel_tree = self.get_channels()
            self._debug("{0}: Channels found for {1} component: {2}",
                        self.name, self.parent.name,
                        ["%s" % x.name for x in self._channel_tree])
        else:
            self._debug("{0}: No channels found", self.name)

    @deprecated
    def checkChannels(self):
        return self.check_channels()

    def get_channels(self):
        if self.parent is not None and self.parent.has_channels:
            return self.parent.get_channels()
        return None

    @deprecated
    def getChannels(self):
        return self.get_channels()

    @property
    def read_cb(self):
        return self._read_cb

    @read_cb.setter
    def read_cb(self, function):
        self._read_cb = function

    @timeit
    def read(self, ch_lst=None, params=None):
        if self._read_cb is not None:
            if self.has_channels and ch_lst is not None:
                if params:
                    ret_value = self._callback_channels(
                        self._read_cb, ch_lst, params)
                else:
                    ret_value = self._callback_channels(self._read_cb, ch_lst)
            else:
                if params:
                    ret_value = self._read_cb(params)
                else:
                    ret_value = self._read_cb()
                self._debug("Attribute {0} read: {1}", self.name, ret_value)
            return self._check_array(ret_value)

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
        root = self._get_root_component()
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
                                      "".format(data_format))
        # prepare the header
        length = str(len(data))
        first_field = str(len(length))
        if len(first_field) > 1:
            self._error("A {0} array cannot be codified", length)
            return float("NaN")
        header = "#%1s%s" % (first_field, length)
        return header + data

    def _get_root_component(self):
        candidate = self.parent
        while candidate.parent is not None:
            candidate = candidate.parent
        return candidate

    @deprecated
    def _getRootComponent(self):
        return self._get_root_component()

    @property
    def write_cb(self):
        return self._write_cb

    @write_cb.setter
    def write_cb(self, function):
        self._write_cb = function

    @timeit
    def write(self, ch_lst=None, value=None):
        self._debug("{0}.write(ch={1}, value={2})", self.name, ch_lst, value)
        if self._write_cb is not None:
            if self.allowed_argins is not None and \
                    value not in self.allowed_argins:
                raise ValueError("Not allowed to write {0}, only {1} are "
                                 "accepted".format(value, self.allowed_argins))
            if self.has_channels and ch_lst is not None:
                ret_value = self._callback_channels(
                    self._write_cb, ch_lst, value)
            else:
                ret_value = self._write_cb(value)
                self._debug("Attribute {0} write {1}: {2}",
                            self.name, value, ret_value)
            return ret_value

    def _callback_channels(self, method_cb, ch_lst, value=None):
        self._check_all_channels_are_within_boundaries(ch_lst)
        if len(ch_lst) == 1:
            ch = ch_lst[0]
            if value is None:
                ret_value = method_cb(ch)
                self._debug("Attribute {0} read from channel {1:d}: {2}",
                            self.name, ch, ret_value)
            else:
                ret_value = method_cb(ch, value)
                self._debug("Attribute {0} write {1} in channel {2:d}: {3}",
                            self.name, value, ch, ret_value)
        else:
            if value is None:
                ret_value = method_cb(ch_lst)
                self._debug("Attribute {0} read for channel set {1}: {2}",
                            self.name, ch_lst, ret_value)
            else:
                ret_value = method_cb(ch_lst, value)
                self._debug("Attribute {0} write {1} for channel set {2}: {3}",
                            self.name, value, ch_lst, ret_value)
        return ret_value

    @deprecated
    def _callbackChannels(self, *args, **kwargs):
        return self._callback_channels(*args, **kwargs)

    def _check_all_channels_are_within_boundaries(self, ch_lst):
        if len(self._channel_tree) != len(ch_lst):
            raise AssertionError("Given channel list hasn't the same number "
                                 "of elements than the known in the tree")
        for i, ch_requested in enumerate(ch_lst):
            lower_bound = self._channel_tree[i].first_channel
            upper_bound = lower_bound + self._channel_tree[i].how_many_channels
            if ch_requested < lower_bound:
                raise AssertionError("below the bounds")
            elif ch_requested >= upper_bound:
                raise AssertionError("above the bounds")

    @deprecated
    def _checkAllChannelsAreWithinBoundaries(self, *args):
        return _check_all_channels_are_within_boundaries(*args)


def build_attribute(name, parent, read_cb=None, write_cb=None, default=False,
                    allowed_argins=None,
                    readcb=None, writecb=None, allowedArgins=None):
    if readcb is not None:
        deprecated_argument("builder", "build_attribute", "readcb")
        if read_cb is None:
            read_cb = readcb
    if writecb is not None:
        deprecated_argument("builder", "build_attribute", "writecb")
        if write_cb is None:
            write_cb = writecb
    if allowedArgins is not None:
        deprecated_argument("builder", "build_attribute", "allowedArgins")
        if allowed_argins is None:
            allowed_argins = allowedArgins
    attr = Attribute(name)
    attr.parent = parent
    if parent is not None and name is not None:
        parent[name] = attr
    attr.read_cb = read_cb
    attr.write_cb = write_cb
    if default:
        parent.default = name
    if allowed_argins:
        attr.allowed_argins = allowed_argins
    attr.check_channels()
    return attr


def BuildAttribute(*args, **kwargs):
    return build_attribute(*args, **kwargs)


class Component(_Logger, dict):
    '''
        Intermediated nodes of the scpi command tree.

        Ex: COMPonent:COMPonent:ATTRibute
    '''

    _parent = None
    _default_key = None
    _how_many = None
    _has_channels = False
    _channel_tree = None
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
                    is_default = " (default {0!r}) ".format(item.default)
                else:
                    is_default = ""
                if isinstance(item, Channel):
                    has_channels = "NN"
                else:
                    has_channels = ""
                repr = "".join("{0}\n{1}{2!r}{3}:{4}{5!r}"
                               "".format(repr, indentation, name, has_channels,
                                         is_default, item))
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
        return self._default_key

    @default.setter
    def default(self, value):
        if value in self.keys():
            self._default_key = value

    @property
    @deprecated
    def _defaultKey(self):
        return self._default_key

    @_defaultKey.setter
    @deprecated
    def _defaultKey(self, value):
        self._default_key = value

    @property
    def has_channels(self):
        return self._has_channels

    @property
    @deprecated
    def hasChannels(self):
        return self.has_channels

    @property
    @deprecated
    def _hasChannels(self):
        return self._has_channels

    @property
    @deprecated
    def _channelTree(self):
        return self._channel_tree

    # TODO: as any Attribute object will search for its channels in its parent
    #       component, as well as the components will search for channels also
    #       over their parents, and they are build from root to leafs:
    #       - once one finds a component with the channel feature, just copy
    #         its tree of the above channels already discovered.
    #       Right now this is following the same path over and over again.

    def check_channels(self):
        if self.parent is not None and self.parent.has_channels:
            self._has_channels = True
            self._channel_tree = self.get_channels()
            self._debug("{0}: Channels found for {1} component: {2}",
                        self.name, self.parent.name,
                        ["%s" % x.name for x in self._channel_tree])
        else:
            self._debug("{0}: No lower level channels found", self.name)

    @deprecated
    def checkChannels(self):
        return self.check_channels()

    def get_channels(self):
        if self.parent is not None and self.parent.has_channels:
            return self.parent.get_channels()
        return None

    @deprecated
    def getChannels(self):
        return self.get_channels()

    # @timeit
    def __getitem__(self, key):
        '''
            Given a key, its identificator is checks if its matches with any of
            the elements in the internal structure, to then return it.
        '''
        if not isinstance(key, DictKey):
            key = DictKey(key)
        try:
            # keys = [hex(k) for k in self._idxs.keys()]
            if int(key) in self._idxs.keys():
                name = self._idxs[int(key)]
                value = dict.__getitem__(self, name)
                # self._debug("getitem key {0} ({1}) in keys() {2}"
                #             "".format(key, hex(int(key)), keys))
                return value
            # else:
            #     self._debug("getitem key {0} ({1}) NOT in keys() {2}"
            #                 "".format(key, hex(int(key)), keys))
        except Exception as exc:
            self._debug("Exception in __getitem__({0} ({1}))"
                        "".format(key, hex(int(key))))
        raise KeyError("{0} ({1}) not found".format(key, hex(int(key))))

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
        keys = [hex(k) for k in self._idxs.keys()]
        # self._debug("setitem {0} ({1}) with {2} together with {3}"
        #             "".format(key, hex(int(key)), value, keys))

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
    def read(self, ch_lst=None, params=None):
        if self._default_key:
            return self.__getitem__(self._default_key).read(ch_lst, params)
        return float('NaN')

    @timeit
    def write(self, ch_lst=None, value=None):
        if self._default_key:
            return self.__getitem__(self._default_key).write(ch_lst, value)
        return float('NaN')


def build_component(name=None, parent=None):
    component = Component(name=name)
    component.parent = parent
    if parent is not None and name is not None:
        parent[name] = component
    component.check_channels()
    return component


@deprecated
def BuildComponent(*args, **kwargs):
    return build_component(*args, **kwargs)


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
        self._read_cb = None
        self._write_cb = None

    @property
    def read_cb(self):
        return self._read_cb

    @property
    @deprecated
    def readcb(self):
        return self.read_cb

    @read_cb.setter
    def read_cb(self, function):
        self._read_cb = function

    @readcb.setter
    @deprecated
    def readcb(self, function):
        self.read_cb = function

    @timeit
    def read(self):
        if self._read_cb is not None:
            return self._read_cb()
        return float("NaN")

    @property
    def write_cb(self):
        return self._write_cb

    @property
    @deprecated
    def writecb(self):
        return self.write_cb

    @write_cb.setter
    def write_cb(self, function):
        self._write_cb = function

    @writecb.setter
    @deprecated
    def writecb(self, function):
        self.write_cb = function

    @timeit
    def write(self, value=None):
        self._debug("{0}.write({1})", self.name, value)
        if self._write_cb is not None:
            if value is not None:
                self._debug("...")
                ret_value = self._write_cb(value)
            else:
                ret_value = self._write_cb()
            self._debug("{0} write({1}): {2}",
                        self.name, value, ret_value)
            return ret_value


def build_special_cmd(name, parent, read_cb, write_cb=None,
                      readcb=None, writecb=None):
    if readcb is not None:
        deprecated_argument("builder", "build_special_cmd", "readcb")
        if read_cb is None:
            read_cb = readcb
    if writecb is not None:
        deprecated_argument("builder", "build_special_cmd", "writecb")
        if write_cb is None:
            write_cb = writecb
    special = SpecialCommand(name)
    special.read_cb = read_cb
    special.write_cb = write_cb
    parent[name.lower()] = special
    return special


@deprecated
def BuildSpecialCmd(*args, **kwargs):
    return build_special_cmd(*args, **kwargs)


class Channel(Component):
    def __init__(self, how_many=None, start_with=None,
                 howMany=None, startWith=None,
                 *args, **kargs):
        super(Channel, self).__init__(*args, **kargs)
        if howMany is not None:
            deprecated_argument("Channel", "__init__", "howMany")
            if how_many is None:
                how_many = howMany
        if startWith is not None:
            deprecated_argument("Channel", "__init__", "startWith")
            if start_with is None:
                start_with = startWith
        if start_with is None:
            start_with = 1
        if len(str(how_many).zfill(2)) > CHNUMSIZE:
            raise ValueError("The number of channels can not exceed "
                             "{0:d} decimal digits".format(CHNUMSIZE))
        self._how_many = how_many
        self._start_with = start_with
        self._has_channels = True
        self._debug("Build a Channel object {0}", self.name)

    def get_channels(self):
        if self.parent is not None and self.parent.has_channels:
            parent_channels = self.parent.get_channels()
            if parent_channels is not None:
                return parent_channels + [self]
        return [self]

    @deprecated
    def getChannels(self):
        return self.get_channels()

    @property
    def how_many_channels(self):
        return self._how_many

    @property
    @deprecated
    def howManyChannels(self):
        return self.how_many_channels

    @property
    def first_channel(self):
        return self._start_with

    @property
    @deprecated
    def firstChannel(self):
        return self.first_channel


def build_channel(name=None, how_many=None, parent=None, start_with=None,
                  howMany=None, startWith=None):
    if howMany is not None:
        deprecated_argument("builder", "build_channel", "howMany")
        if how_many is None:
            how_many = howMany
    if startWith is not None:
        deprecated_argument("builder", "build_channel", "startWith")
        if start_with is None:
            start_with = startWith
    if start_with is None:
        start_with = 1
    channel = Channel(name=name, how_many=how_many, start_with=start_with)
    channel.parent = parent
    if parent is not None and name is not None:
        parent[name] = channel
    channel.check_channels()
    return channel


@deprecated
def BuildChannel(*args, **kwargs):
    return build_channel(*args, **kwargs)
