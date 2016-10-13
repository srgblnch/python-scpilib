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

__author__ = "Sergi Blanch-Torné"
__copyright__ = "Copyright 2015, CELLS / ALBA Synchrotron"
__license__ = "GPLv3+"

__all__ = ["Locker"]


from datetime import datetime as _datetime
from datetime import timedelta as _timedelta
try:
    from .logger import Logger as _Logger
except:
    from logger import Logger as _Logger
from time import sleep as _sleep
from threading import currentThread as _currentThread
from traceback import print_exc


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


# --- testing area
try:
    from .logger import printHeader as _printHeader
    from .logger import printFooter as _printFooter
except:
    from logger import printHeader as _printHeader
    from logger import printFooter as _printFooter
from threading import Event as _Event
from threading import Lock as _Lock
from threading import Thread as _Thread


TEST_EXPIRATION_TIME = 10  # seconds


def _printInfo(msg, level=0, lock=None, top=False, bottom=False):
    if lock is None:
        print("%s%s" % ("\t"*level, msg))
    else:
        with lock:
            tab = "\t"*level
            msg = "Thread %s: %s" % (_currentThread().name, msg)
            if top or bottom:
                if top:
                    msg = "%s%s\n%s%s" % (tab, "-"*len(msg), tab, msg)
                elif bottom:
                    msg = "%s%s\n%s%s\n" % (tab, msg, tab, "-"*len(msg))
            else:
                msg = "%s%s" % (tab, msg)
            print(msg)


def lockTake(lockObj):
    testName = "Initial state test"
    _printHeader("Test the initial state of the %s object" % lockObj)
    _printInfo("%r" % (lockObj), 1)

    _printInfo("Check if it is lock", level=1, top=True)
    if lockObj.isLock():
        return False, "%s FAILED" % (testName)
    _printInfo("%s is not lock" % (lockObj), level=1, bottom=True)

    _printInfo("Check if it lock can be requested", level=1, top=True)
    if not lockObj.request():
        return False, "%s FAILED" % (testName)
    _printInfo("%r is now lock" % (lockObj), level=1, bottom=True)

    _printInfo("Check if it lock can be released", level=1, top=True)
    if not lockObj.release():
        return False, "%s FAILED" % (testName)
    _printInfo("%r is now released" % (lockObj), level=1, bottom=True)

    return True, "%s PASSED" % (testName)


def multithreadingTake(lockObj):
    def sendEvent(eventLst, who):
        eventLst[who].set()
        while eventLst[who].isSet():  # wait to the thread to work
            _sleep(1)
    testName = "Lock take test"
    _printHeader("%s for %s" % (testName, lockObj))
    joinerEvent = _Event()
    joinerEvent.clear()
    userThreads = []
    requestEvents = []
    accessEvents = []
    releaseEvents = []
    printLock = _Lock()
    for i in range(2):
        requestEvent = _Event()
        accessEvent = _Event()
        releaseEvent = _Event()
        userThread = _Thread(target=threadFunction,
                             args=(lockObj, joinerEvent,
                                   requestEvent, accessEvent, releaseEvent,
                                   printLock),
                             name='%d' % (i))
        requestEvents.append(requestEvent)
        accessEvents.append(accessEvent)
        releaseEvents.append(releaseEvent)
        userThreads.append(userThread)
        userThread.start()
    # here is where the test starts ---
    try:
        _printInfo("Initial state %r\n" % (lockObj),
                   level=1, lock=printLock)
        if lockObj.isLock():
            return False, "%s FAILED" % (testName)

        _printInfo("Tell the threads to access",
                   level=1, lock=printLock, top=True)
        sendEvent(accessEvents, 0)
        sendEvent(accessEvents, 1)
        _printInfo("both should have had access",
                   level=1, lock=printLock, bottom=True)

        _printInfo("Thread 0 take the lock",
                   level=1, lock=printLock, top=True)
        sendEvent(requestEvents, 0)
        if not lockObj.isLock() or lockObj.owner != '0':
            raise Exception("It shall be lock by 0")
        _printInfo("Tell the threads to access",
                   level=1, lock=printLock)
        sendEvent(accessEvents, 0)
        sendEvent(accessEvents, 1)
        _printInfo("0 should, but 1 don't",
                   level=1, lock=printLock, bottom=True)

        _printInfo("Try to lock when it is already",
                   level=1, lock=printLock, top=True)
        sendEvent(requestEvents, 1)
        if not lockObj.isLock() or lockObj.owner != '0':
            raise Exception("It shall be lock by user 0")
        _printInfo("Tell the threads to access",
                   level=1, lock=printLock)
        sendEvent(accessEvents, 0)
        sendEvent(accessEvents, 1)
        _printInfo("0 should, but 1 don't",
                   level=1, lock=printLock, bottom=True)

        _printInfo("Try to release by a NON-owner",
                   level=1, lock=printLock, top=True)
        sendEvent(releaseEvents, 1)
        if not lockObj.isLock() or lockObj.owner != '0':
            raise Exception("It shall be lock by user 0")
        _printInfo("Tell the threads to access",
                   level=1, lock=printLock)
        sendEvent(accessEvents, 0)
        sendEvent(accessEvents, 1)
        _printInfo("0 should, but 1 don't",
                   level=1, lock=printLock, bottom=True)

        _printInfo("release the lock",
                   level=1, lock=printLock, top=True)
        sendEvent(releaseEvents, 0)
        if lockObj.isLock():
            raise Exception("It shall be released")
        _printInfo("Tell the threads to access",
                   level=1, lock=printLock)
        sendEvent(accessEvents, 0)
        sendEvent(accessEvents, 1)
        _printInfo("both should have had to",
                   level=1, lock=printLock, bottom=True)

        # TODO: timeout
        _printInfo("Thread 1 take the lock and expire it",
                   level=1, lock=printLock, top=True)
        sendEvent(requestEvents, 1)
        if not lockObj.isLock() or lockObj.owner != '1':
            raise Exception("It shall be lock by 1")
        _printInfo("Tell the threads to access",
                   level=1, lock=printLock)
        sendEvent(accessEvents, 0)
        sendEvent(accessEvents, 1)
        _printInfo("1 should, but 0 don't",
                   level=1, lock=printLock)
        _printInfo("Sleep %d seconds to expire the lock"
                   % TEST_EXPIRATION_TIME,
                   level=1, lock=printLock)
        _sleep(TEST_EXPIRATION_TIME)
        _printInfo("Tell the threads to access",
                   level=1, lock=printLock)
        sendEvent(accessEvents, 0)
        sendEvent(accessEvents, 1)
        _printInfo("both should have had to",
                   level=1, lock=printLock, bottom=True)

        answer = True, "%s PASSED" % (testName)
    except Exception as e:
        print(e)
        print_exc()
        answer = False, "%s FAILED" % (testName)
    joinerEvent.set()
    while len(userThreads) > 0:
        userThread = userThreads.pop()
        userThread.join(1)
        if userThread.isAlive():
            userThreads.append(userThread)
    print("All threads has finished")
    return answer


def threadFunction(lockObj, joinedEvent, request, access, release, printLock):
    _printInfo("started", level=1, lock=printLock)
    while not joinedEvent.isSet():
        # _printInfo("loop", level=1, lock=printLock)
        if request.isSet():
            take = lockObj.request(TEST_EXPIRATION_TIME)
            request.clear()
            _printInfo("request %s" % take, level=2, lock=printLock)
        if access.isSet():
            if lockObj.access():
                _printInfo("access allowed", level=2, lock=printLock)
            else:
                _printInfo("rejected to access", level=2, lock=printLock)
            access.clear()
        if release.isSet():
            free = lockObj.release()
            release.clear()
            _printInfo("release %s" % free, level=2, lock=printLock)
        _sleep(1)
    _printInfo("exit", level=1, lock=printLock)


def main():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('', "--debug", action="store_true", default=False,
                      help="Set the debug flag")
    (options, args) = parser.parse_args()
    lockObj = Locker(name='LockerTest', debug=options.debug)
    print("\nBasic locker functionality test:")
    results = []
    messages = []
    for test in [lockTake, multithreadingTake]:
        result, msg = test(lockObj)
        results.append(result)
        messages.append(msg)
        _printFooter(msg)
    if all(results):
        print("All tests PASSED")
    else:
        print("ALERT! NOT ALL THE TESTS HAS PASSED. Check the list")
    for msg in messages:
        print(msg)


if __name__ == '__main__':
    main()
