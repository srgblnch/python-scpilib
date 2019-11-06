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


from __future__ import print_function
try:
    import __builtin__
except ValueError:
    # Python 3
    import builtins as __builtin__
from datetime import datetime as _datetime
import logging as _logging
from logging import handlers as _handlers
from multiprocessing import current_process as _currentProcess
from numpy import array, append
import os
from time import time
from threading import currentThread as _currentThread
from threading import Lock as _Lock
from weakref import ref as _weakref


__author__ = "Sergi Blanch-Torné"
__email__ = "sblanch@cells.es"
__copyright__ = "Copyright 2015, CELLS / ALBA Synchrotron"
__license__ = "GPLv3+"


global lock
lock = _Lock()
_debug_ = False
_log2file_ = True
_timeit_collect_ = False
_deprecate_collect_ = True


def scpi_debug(value):
    global _debug_
    _debug_ = value


def scpi_log2file(value):
    global _log2file_
    _log2file_ = value


def scpi_timeit_collection(value):
    global _timeit_collect_
    _timeit_collect_ = value


_logger_NOTSET = _logging.NOTSET  # 0
_logger_CRITICAL = _logging.CRITICAL  # 50
_logger_ERROR = _logging.ERROR  # 40
_logger_WARNING = _logging.WARNING  # 30
_logger_INFO = _logging.INFO  # 20
_logger_DEBUG = _logging.DEBUG  # 10


__all__ = ["scpi_debug", "scpi_log2file", "scpi_timeit_collection",
           "trace", "timeit", "deprecated",
           "timeit_collection", "deprecation_collection",
           "Logger"]


timeit_collection = {}
deprecation_collection = {}


def debug_stream(msg):
    __builtin__.print("{0:f} -- {1}".format(time(), msg))


def _get_printer(obj):
    if hasattr(obj, "debug_stream"):
        return obj.debug_stream
    return debug_stream


def trace(method):
    def _compact_args(lst_args, dct_args):
        lst_str = "*args: {0}".format(lst_args) if len(lst_args) > 0 else ""
        dct_str = "**kwargs: {0}".format(dct_args) if len(dct_args) > 0 else ""
        if len(lst_str) > 0 and len(dct_args) > 0:
            return "{0}, {1}".format(lst_str, dct_str)
        elif len(lst_str) > 0:
            return "{0}".format(lst_str)
        elif len(dct_str) > 0:
            return "{0}".format(dct_str)
        return ""

    def _compact_answer(answer):
        if isinstance(answer, str) and len(answer) > 100:
            return "{0}...{1}".format(answer[:25], answer[-25:])
        return "{0}".format(answer)

    def logging(*args, **kwargs):
        if _debug_:
            self = args[0]
            klass = self.__class__.__name__
            method_name = method.__name__
            args_str = _compact_args(args[1:], kwargs)
            printer = _get_printer(self)
            printer("> {0}.{1}({2})"
                    "".format(klass, method_name, args_str))
        answer = method(*args, **kwargs)
        if _debug_:
            answer_str = _compact_answer(answer)
            printer("< {0}.{1}: {2}"
                    "".format(klass, method_name, answer_str))
        return answer
    return logging


def timeit(method):
    def measure(*args, **kwargs):
        if _timeit_collect_:
            self = args[0]
            klass = self.__class__.__name__
            if klass not in timeit_collection:
                timeit_collection[klass] = {}
            method_name = method.__name__
            if method_name not in timeit_collection[klass]:
                timeit_collection[klass][method_name] = array([])
            t_0 = time()
        answer = method(*args, **kwargs)
        if _timeit_collect_:
            t_diff = time()-t_0
            timeit_collection[klass][method_name] = append(
                timeit_collection[klass][method_name], t_diff)
        return answer

    return measure


def deprecated(method):
    def collect(*args, **kwargs):
        if _deprecate_collect_:
            self = args[0]
            klass = self.__class__.__name__
            if klass not in deprecation_collection:
                deprecation_collection[klass] = {}
            method_name = method.__name__
            if method_name not in deprecation_collection[klass]:
                deprecation_collection[klass][method_name] = 0
        answer = method(*args, **kwargs)
        if _deprecate_collect_:
            deprecation_collection[klass][method_name] += 1
        return answer

    return collect


class Logger(object):
    '''This class is a very basic debugging flag mode used as a super class
       for the other classes in this library.
    '''

    _name = None
    _levelStr = {_logger_NOTSET:   '',
                 _logger_CRITICAL: 'CRITICAL',
                 _logger_ERROR:    'ERROR',
                 _logger_WARNING:  'WARNING',
                 _logger_INFO:     'INFO',
                 _logger_DEBUG:    'DEBUG'}

    def __init__(self, name="Logger", loggerName=None, log2file=False,
                 debug=False, *args, **kwargs):
        super(Logger, self).__init__(*args, **kwargs)
        self._name = name
        self.__debugFlag = None
        self.__debuglevel = _logger_NOTSET
        self.__log2file = log2file
        self.__loggerName = loggerName or "SCPI"
        self.__logging_folder = None
        self.__logging_file = None
        self._devlogger = _logging.getLogger(self.__loggerName)
        self._handler = None
        # setup ---
        self.logEnable(True)
        if debug or _debug_:
            self.logLevel(_logger_DEBUG)
        else:
            self.logLevel(_logger_INFO)
        if _log2file_:
            self.log2File(True)
        self.loggingFile()
        if not len(self._devlogger.handlers):
            self._devlogger.setLevel(_logger_DEBUG)
            self._handler = \
                _handlers.RotatingFileHandler(self.__logging_file,
                                              maxBytes=10000000,
                                              backupCount=5)
            self._handler.setLevel(_logger_NOTSET)
            formatter = _logging.Formatter('%(asctime)s - %(levelname)-7s - '
                                           '%(name)s - %(message)s')
            self._handler.setFormatter(formatter)
            self._devlogger.addHandler(self._handler)
        else:
            self._handler = self._devlogger.handlers[0]

    @property
    def name(self):
        return self._name

    @property
    def depth(self):
        depth = 0
        if hasattr(self, '_parent'):
            parent = self._parent
            while parent is not None:
                parent = parent._parent
                depth += 1
        return depth

    @property
    def devlogger(self):
        return self._devlogger

    @devlogger.setter
    def devlogger(self, devlogger):
        self._devlogger = devlogger

    @property
    def handler(self):
        return self._handler

    def addHandler(self, handler):
        self._devlogger.addHandler(handler)

    def removeHandler(self, handler=None):
        if handler:
            self._devlogger.removeHandler(handler)
        else:
            self._devlogger.removeHandler(self._handler)

    def replaceHandler(self, handler):
        self._devlogger.removeHandler(self._handler)
        self._devlogger.addHandler(handler)
        self._handler = handler

    def loggingFolder(self):
        if self.__logging_folder is None:
            logging_folder = "/var/log/{0}".format(self.__loggerName)
            if not self.__buildLoggingFolder(logging_folder):
                logging_folder = "/tmp/log/{0}".format(self.__loggerName)
                if not self.__buildLoggingFolder(logging_folder):
                    raise SystemError("No folder for logging available")
            self.__logging_folder = logging_folder
        else:
            if not self.__buildLoggingFolder(self.__logging_folder):
                raise SystemError("No folder for logging available")
        return self.__logging_folder

    def __buildLoggingFolder(self, folder):
        try:
            if not os.path.exists(folder):
                os.makedirs(folder)
            return True
        except Exception:
            return False

    def loggingFile(self):
        if self.__logging_file is None:
            self.__logging_file = "{0}/{1}.log".format(
                self.loggingFolder(), self.__loggerName)
        return self.__logging_file

    def log2File(self, boolean):
        if type(boolean) is not bool:
            raise AssertionError("The parameter must be a boolean")
        self.__log2file = boolean

    def logEnable(self, dbg=False):
        if type(dbg) is not bool:
            raise AssertionError("The parameter must be a boolean")
        self.__debugFlag = dbg

    def logState(self):
        return self.__debugFlag

    def logLevel(self, level):
        try:
            self.__debuglevel = int(level)
        except Exception:
            raise AssertionError("The loglevel must be an integer")
        self._devlogger.setLevel(level)
        if self._handler is not None:
            self._handler.setLevel(level)

    def logGetLevel(self):
        return self.__debuglevel

    @property
    def _processId(self):
        return _currentProcess().name

    @property
    def _threadId(self):
        return _currentThread().getName()

    def logMessage(self, msg, level):
        _tag = self._levelStr[level]
        if self.__log2file:
            method = {_logger_CRITICAL: self._devlogger.critical,
                      _logger_ERROR: self._devlogger.error,
                      _logger_WARNING: self._devlogger.warn,
                      _logger_INFO: self._devlogger.info,
                      _logger_DEBUG: self._devlogger.debug}
            method[level]("{0}: {1}".format(self.name, msg))

    def _critical(self, msg, *args):
        try:
            if len(args) > 0:
                msg = msg.format(*args)
            self.logMessage(msg, _logger_CRITICAL)
        except Exception as exc:
            self.logMessage("Cannot log {0!r} because {1}".format(msg, exc),
                            _logger_CRITICAL)

    def _error(self, msg, *args):
        try:
            if len(args) > 0:
                msg = msg.format(*args)
            self.logMessage(msg, _logger_ERROR)
        except Exception as exc:
            self.logMessage("Cannot log {0!r} because {1}".format(msg, exc),
                            _logger_CRITICAL)

    def _warning(self, msg, *args):
        try:
            if len(args) > 0:
                msg = msg.format(*args)
            self.logMessage(msg, _logger_WARNING)
        except Exception as exc:
            self.logMessage("Cannot log {0!r} because {1}".format(msg, exc),
                            _logger_CRITICAL)

    def _info(self, msg, *args):
        try:
            if len(args) > 0:
                msg = msg.format(*args)
            self.logMessage(msg, _logger_INFO)
        except Exception as exc:
            self.logMessage("Cannot log {0!r} because {1}".format(msg, exc),
                            _logger_CRITICAL)

    def _debug(self, msg, *args):
        try:
            if self.__debugFlag:
                if len(args) > 0:
                    msg = msg.format(*args)
                self.logMessage(msg, _logger_DEBUG)
        except Exception as exc:
            self.logMessage("Cannot log {0!r} because {1}".format(msg, exc),
                            _logger_CRITICAL)
