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
from datetime import timedelta as _timedelta
try:
    from .logger import Logger as _Logger
except:
    from logger import Logger as _Logger
from threading import currentThread as _currentThread


__author__ = "Sergi Blanch-Torné"
__copyright__ = "Copyright 2016, CELLS / ALBA Synchrotron"
__license__ = "GPLv3+"

__all__ = ["Locker"]


DEFAULT_EXPIRATION_TIME = 60  # seconds
UPPER_LIMIT_EXPIRATION_TIME = _timedelta(0, DEFAULT_EXPIRATION_TIME*10, 0)


class Locker(_Logger):
    """
        Object to control the access to certain areas of the code, similar idea
        than a Semaphore or a Lock from the threading library, but not the
        same.

        An external process talks with a service thread, and what the thread
        does
    """
    def __init__(self, *args, **kargs):
        super(Locker, self).__init__(*args, **kargs)
        self._owner = None
        self._when = None
        self._expiration = _timedelta(0, DEFAULT_EXPIRATION_TIME, 0)

    def __str__(self):
        return "%s(%s)"\
            % (self.name, "" if self._owner is None else self._owner)

    def __repr__(self):
        return "%s(owner=%s, when=%s, expiration=%s)"\
            % (self.name, self._owner, self._when, self._expiration)

    @property
    def owner(self):
        return self._owner

    def Owner(self):
        return self.owner

    # API ---

    def request(self, timeout=None):
        """
            Request to book the access. If its free (or has expired a previous
            one) do it, else reject (even if the owner recalls it).
        """
        # self._debug("%s request()" % _currentThread().name)
        if not self._hasOwner() or self._hasExpired():
            self._doLock(timeout)
            return True
        else:
            self._warning("%s request the lock when already is"
                          % (_currentThread().name))
            return False

    def release(self):
        """
            Only the owner can release the lock.
        """
        # self._debug("%s release()" % _currentThread().name)
        if self._isOwner():
            self._debug("%s releases the lock" % self._owner)
            self._doRelease()
            return True
        else:
            self._error("%s is NOT allowed to release %s's lock"
                        % (_currentThread().name, self._owner))
            return False

    def access(self):
        """
            Request if the give thread is allowed to access the resource.
        """
        # self._debug("%s access()" % _currentThread().name)
        if not self.isLock():
            self._debug("There is no owner of the lock, %s can pass"
                        % _currentThread().name)
            return True
        elif self._isOwner():
            self._when = _datetime.now()
            self._debug("The owner is who is asking (%s), "
                        "renew its booking" % (_currentThread().name))
            return True
        else:
            return False

    def isLock(self):
        """
            Check if the lock is owned.
        """
        # self._debug("%s isLock()" % _currentThread().name)
        if self._hasOwner() and not self._hasExpired():
            return True
        return False

    @property
    def expirationTime(self):
        return self._expiration

    @expirationTime.setter
    def expirationTime(self, value):
        if not self._hasExpired() or self._isOwner():
            self._setExpiration(value)
        else:
            raise EnvironmentError("Only the owner can change the expiration")

    # force area ---

    def _forceRelease(self):
        self._warning("Locker forced to be released!")
        self._doRelease()

    def _forceLock(self):
        self._forceRelease()
        self._doLock()

    # internal methods ---

    def _hasOwner(self):
        hasOwner = self._owner is not None
#         if hasOwner:
#             self._debug("Lock has owner (%s)" % self._owner)
#         else:
#             self._debug("Lock is free")
        return hasOwner

    def _isOwner(self):
        isOwner = self._owner == _currentThread().name
#         if isOwner:
#             self._debug("%s is the owner" % (_currentThread().name))
#         else:
#             self._debug("%s is NOT the owner" % (_currentThread().name))
        return isOwner

    def _doLock(self, timeout=None):
        if self._hasOwner():
            raise RuntimeError("Try to lock when not yet released")
        self._owner = _currentThread().name
        self._when = _datetime.now()
        self.expirationTime = timeout
        self._info("%s has take the lock (expiration time %s)"
                   % (self.owner, self.expirationTime))

    def _doRelease(self):
        self._owner = None
        self._when = None
        self._expiration = None

    def _setExpiration(self, value):
        if value is None:
            value = DEFAULT_EXPIRATION_TIME
        try:
            value = int(value)
        except Exception as e:
            raise TypeError("Expiration time assignment must be an integer")
        try:
            value = _timedelta(0, value, 0)
        except Exception as e:
            raise ValueError("Value cannot be understood as a delta time")
        if value > UPPER_LIMIT_EXPIRATION_TIME:
            raise OverflowError("Too big expiration time")
        else:
            self._expiration = value

    def _hasExpired(self):
        if self._when is None or self._expiration is None:
            # TBD: in fact here there is nothing to expire
            return True
        delta = _datetime.now() - self._when
        if delta > self._expiration:
            self._info("No news from the lock owner (%s) after %s: release "
                       "the lock." % (self._owner, delta))
            self._doRelease()
            return True
        self._debug("lock NOT expired, still %s for %s" % (delta, self._owner))
        return False
