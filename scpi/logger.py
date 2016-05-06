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

from datetime import datetime as _datetime
from threading import currentThread as _currentThread
from threading import Lock as _Lock
from weakref import ref as _weakref

global lock
lock = _Lock()

_logger_ERROR = 1
_logger_WARNING = 2
_logger_INFO = 3
_logger_DEBUG = 4


class Logger(object):
    '''This class is a very basic debugging flag mode used as a super class
       for the other classes in this library.
    '''

    _type = {_logger_ERROR:   'ERROR',
             _logger_WARNING: 'WARNING',
             _logger_INFO:    'INFO',
             _logger_DEBUG:   'DEBUG'}

    def __init__(self, name="Logger", debug=False):
        super(Logger, self).__init__()
        self._name = name
        self._debugFlag = debug

    @property
    def depth(self):
        depth = 0
        parent = self._parent
        while parent is not None:
            parent = parent._parent
            depth += 1
        return depth

    @property
    def _threadId(self):
        return _currentThread().getName()

    def _print(self, msg, type):
        with lock:
            when = _datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            print("%s\t%s\t%s\t%s\t%s"
                  % (self._threadId, type, when, self._name, msg))

    def _error(self, msg):
        self._print(msg, self._type[_logger_ERROR])

    def _warning(self, msg):
        self._print(msg, self._type[_logger_WARNING])

    def _info(self, msg):
        self._print(msg, self._type[_logger_INFO])

    def _debug(self, msg):
        if self._debugFlag:
            self._print(msg, self._type[_logger_DEBUG])

# for testing section


def printHeader(msg):
    print("\n"+"="*len(msg)+"\n"+msg+"\n"+"="*len(msg)+"\n")


def printFooter(msg):
    print("\n*** %s ***\n" % (msg))
