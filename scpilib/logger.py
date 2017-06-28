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

from datetime import datetime as _datetime
import logging as _logging
from logging import handlers as _handlers
from multiprocessing import current_process as _currentProcess
import os
from threading import currentThread as _currentThread
from threading import Lock as _Lock
from weakref import ref as _weakref


__author__ = "Sergi Blanch-Torné"
__email__ = "sblanch@cells.es"
__copyright__ = "Copyright 2015, CELLS / ALBA Synchrotron"
__license__ = "GPLv3+"


global lock
lock = _Lock()

_logger_NOTSET = _logging.NOTSET  # 0
_logger_CRITICAL = _logging.CRITICAL  # 50
_logger_ERROR = _logging.ERROR  # 40
_logger_WARNING = _logging.WARNING  # 30
_logger_INFO = _logging.INFO  # 20
_logger_DEBUG = _logging.DEBUG  # 10


__all__ = ["Logger"]


class Logger(object):
    '''This class is a very basic debugging flag mode used as a super class
       for the other classes in this library.
    '''

    _levelStr = {_logger_NOTSET:   '',
                 _logger_CRITICAL: 'CRITICAL',
                 _logger_ERROR:    'ERROR',
                 _logger_WARNING:  'WARNING',
                 _logger_INFO:     'INFO',
                 _logger_DEBUG:    'DEBUG'}

    def __init__(self, name="Logger", debug=False, loggerName=None,
                 log2File=False, *args, **kwargs):
        super(Logger, self).__init__(*args, **kwargs)
        # prepare vbles ---
        self._name = name
        self.__debugFlag = None
        self.__debuglevel = _logger_NOTSET
        self.__log2file = log2File
        self.__loggerName = loggerName or "SCPI"
        self.__logging_folder = None
        self.__logging_file = None
        self._devlogger = _logging.getLogger(self.__loggerName)
        self._handler = None
        # setup ---
        self.logEnable(True)
        if debug:
            self.logLevel(_logger_DEBUG)
        else:
            self.logLevel(_logger_INFO)
        self.loggingFile()
        if not len(self._devlogger.handlers):
            self._devlogger.setLevel(_logger_DEBUG)
            self._handler = \
                _handlers.RotatingFileHandler(self.__logging_file,
                                              maxBytes=10000000,
                                              backupCount=5)
            self._handler.setLevel(_logger_NOTSET)
            formatter = _logging.Formatter('%(asctime)s - %(levelname)s - '
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
            logging_folder = "/var/log/%s" % (self.__loggerName)
            if not self.__buildLoggingFolder(logging_folder):
                logging_folder = "/tmp/log/%s" % (self.__loggerName)
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
        except:
            return False

    def loggingFile(self):
        if self.__logging_file is None:
            self.__logging_file = \
                "%s/%s.log" % (self.loggingFolder(), self.__loggerName)
        return self.__logging_file

    def log2File(self, boolean):
        if type(boolean) is not bool:
            raise AssertionError("The parameter must be a boolean")
        self.__log2file = boolean
        self.logMessage("log2File() set to %s"
                        % (self.__log2file), _logger_INFO)

    def logEnable(self, dbg=False):
        if type(dbg) is not bool:
            raise AssertionError("The parameter must be a boolean")
        self.__debugFlag = dbg
        self.logMessage("logEnable()::Debug flag set to %s"
                        % (self.__debugFlag), _logger_INFO)

    def logState(self):
        return self.__debugFlag

    def logLevel(self, level):
        try:
            self.__debuglevel = int(level)
        except:
            raise AssertionError("The loglevel must be an integer")
        self._devlogger.setLevel(level)
        if self._handler is not None:
            self._handler.setLevel(level)
        self.logMessage("logEnable()::Debug level set to %s"
                        % (self.__debuglevel), _logger_INFO)
#         if self._handler is not None:
#             self._handler.setLevel(level)
#         self.logMessage("logEnable()::Debug level set to %s"
#                         % (self.__debuglevel), _logger_INFO)

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
        prt_msg = "%s - %s - %s" % (_tag, self.__loggerName, msg)
        if self.__log2file:
            method = {_logger_CRITICAL: self._devlogger.critical,
                      _logger_ERROR: self._devlogger.error,
                      _logger_WARNING: self._devlogger.warn,
                      _logger_INFO: self._devlogger.info,
                      _logger_DEBUG: self._devlogger.debug}
            method[level](msg)

    def _critical(self, msg):
        self.logMessage(msg, _logger_CRITICAL)

    def _error(self, msg):
        self.logMessage(msg, _logger_ERROR)

    def _warning(self, msg):
        self.logMessage(msg, _logger_WARNING)

    def _info(self, msg):
        self.logMessage(msg, _logger_INFO)

    def _debug(self, msg):
        if self.__debugFlag:
            self.logMessage(msg, _logger_DEBUG)
