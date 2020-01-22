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
    from .logger import deprecated, deprecated_argument
except Exception:
    from logger import Logger as _Logger
    from logger import deprecated, deprecated_argument
from threading import currentThread as _current_thread


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
        return "{0}({1})".format(self.name,
                                 "" if self._owner is None else self._owner)

    def __repr__(self):
        return "{0}(owner={1}, when={2}, expiration={3})" \
               "".format(self.name, self._owner, self._when, self._expiration)

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
        # self._debug("%s request()" % _current_thread().name)
        if not self._hasOwner() or self._hasExpired():
            self._doLock(timeout)
            return True
        else:
            self._warning("{0} request the lock when already is",
                          _current_thread().name)
            return False

    def release(self):
        """
            Only the owner can release the lock.
        """
        # self._debug("%s release()" % _current_thread().name)
        if self._isOwner():
            self._debug("{0} releases the lock", self._owner)
            self._doRelease()
            return True
        else:
            self._error("{0} is NOT allowed to release {1}'s lock",
                        _current_thread().name, self._owner)
            return False

    def access(self):
        """
            Request if the give thread is allowed to access the resource.
        """
        # self._debug("%s access()" % _current_thread().name)
        if not self.isLock():
            self._debug("There is no owner of the lock, {0} can pass",
                        _current_thread().name)
            return True
        elif self._isOwner():
            self._when = _datetime.now()
            self._debug("The owner is who is asking ({0}), "
                        "renew its booking", _current_thread().name)
            return True
        else:
            return False

    def isLock(self):
        """
            Check if the lock is owned.
        """
        # self._debug("%s isLock()" % _current_thread().name)
        if self._hasOwner() and not self._hasExpired():
            return True
        return False

    @property
    def expiration_time(self):
        return self._expiration

    @property
    @deprecated
    def expirationTime(self):
        return self.expiration_time

    @expiration_time.setter
    def expiration_time(self, value):
        if not self._hasExpired() or self._isOwner():
            self._setExpiration(value)
        else:
            raise EnvironmentError("Only the owner can change the expiration")

    @expirationTime.setter
    @deprecated
    def expirationTime(self, value):
        self.expiration_time = value

    # force area ---

    def _force_release(self):
        self._warning("Locker forced to be released!")
        self._do_release()

    @deprecated
    def _forceRelease(self):
        self._forceRelease()

    def _force_lock(self):
        self._force_release()
        self._do_lock()

    @deprecated
    def _forceLock(self):
        self._force_lock()

    # internal methods ---

    def _has_owner(self):
        has_owner = self._owner is not None
#         if has_owner:
#             self._debug("Lock has owner ({0})", self._owner)
#         else:
#             self._debug("Lock is free")
        return has_owner

    @deprecated
    def _hasOwner(self):
        return self._has_owner()

    def _is_owner(self):
        is_owner = self._owner == _current_thread().name
#         if is_owner:
#             self._debug("{0} is the owner", _current_thread().name)
#         else:
#             self._debug("{1} is NOT the owner", _current_thread().name)
        return is_owner

    @deprecated
    def _isOwner(self):
        return self._is_owner()

    def _do_lock(self, timeout=None):
        if self._has_owner():
            raise RuntimeError("Try to lock when not yet released")
        self._owner = _current_thread().name
        self._when = _datetime.now()
        self.expiration_time = timeout
        self._info("{0} has take the lock (expiration time {1})",
                   self.owner, self.expiration_time)

    @deprecated
    def _doLock(self, *args, **kwargs):
        return self._do_lock(*args, **kwargs)

    def _do_release(self):
        self._owner = None
        self._when = None
        self._expiration = None

    @deprecated
    def _doRelease(self):
        return self._do_release()

    def _set_expiration(self, value):
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

    @deprecated
    def _setExpiration(self, *args, **kwargs):
        return self._set_expiration(*args, **kwargs)

    def _has_expired(self):
        if self._when is None or self._expiration is None:
            # TBD: in fact here there is nothing to expire
            return True
        delta = _datetime.now() - self._when
        if delta > self._expiration:
            self._info("No news from the lock owner ({0}) after {1}: release "
                       "the lock.", self._owner, delta)
            self._do_release()
            return True
        self._debug("lock NOT expired, still {0} for {1}", delta, self._owner)
        return False

    @deprecated
    def _hasExpired(self):
        return self._has_expired()
