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
    def __init__(self, *args, **kargs):
        super(Locker, self).__init__(*args, **kargs)
        self._owner = None
        self._when = None
        self._expiration = _timedelta(0, DEFAULT_EXPIRATION_TIME, 0)

    def __str__(self):
        return "%s(%s)"\
            % (self.name,
               "" if self._owner is None else self._owner)

    def __repr__(self):
        return "%s(%s, %s, %s)"\
            % (self.name, self._owner, self._when, self._expiration)

    @property
    def owner(self):
        return self._owner

    def Owner(self):
        return self.owner

    def release(self):
        if self._owner == _currentThread().name:
            self._debug("%s releases the lock" % self._owner)
            self._owner = None
            self._when = None
            self._expiration = _timedelta(0, DEFAULT_EXPIRATION_TIME, 0)
            return True
        else:
            self._error("%s is NOT allowed to release %s's lock"
                        % (_currentThread().name, self._owner))
            return False

    def _forceRelease(self):
        self._warning("Locker forced to be released!")
        self._owner = None
        self._when = None
        self._expiration = _timedelta(0, DEFAULT_EXPIRATION_TIME, 0)

    def request(self, timeout=None):
        self.hasExpired()
        if self._owner is None:
            self._owner = _currentThread().name
            self._when = _datetime.now()
            if timeout is not None:
                try:
                    expirationRequest = _timedelta(0, timeout, 0)
                    if expirationRequest > UPPER_LIMIT_EXPIRATION_TIME:
                        raise OverflowError("Too big expiration time")
                    self._expiration = expirationRequest
                except Exception as e:
                    self._error("request timeout %r invalid: %s"
                                % (timeout, e))
                    return False
            self._info("%s has take the lock (expiration time %s)"
                       % (self.owner, self.expirationTime))
            return True
        return False

    def isLock(self):
        if self._owner is None:
            self._debug("There is no owner of the lock, %s can pass"
                        % _currentThread().name)
            return False
        # if who is asking if in fact the owner of the lock, it has the right
        # to pass. And the watchdog feature will renew its timeout.
        if self._owner == _currentThread().name:
            self._when = _datetime.now()
            self._debug("The owner is who is asking (%s), "
                        "renew the its booking" % (_currentThread().name))
            return False
        # when someone else ask if the lock allows it to pass, it has to be
        # checked if the owner has overcome its expiration time.
        return not self.hasExpired()

    @property
    def expirationTime(self):
        return self._expiration

    @expirationTime.setter
    def expirationTime(self, value):
        try:
            value = int(value)
        except Exception as e:
            raise TypeError("Expiration time assignment must be an integer")
        else:
            self._expiration = _timedelta(0, value, 0)

    def hasExpired(self):
        if self._when is None:
            self._debug("No expiration time set")
            return True  # TBD: in fact here there is nothing to expire
        delta = _datetime.now() - self._when
        if delta > self._expiration:
            self._info("No news from the lock owner (%s) after %s: release "
                       "the lock." % (self._owner, delta))
            self._forceRelease()
            return True
        self._debug("lock not expired, still %s for %s" % (delta, self._owner))
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


def _printInfo(msg, level=0, lock=None):
    if lock is None:
        print("%s%s" % ("\t"*level, msg))
    else:
        with lock:
            print("%sThread %s %s" % ("\t"*level, _currentThread().name, msg))


def lockTake(lockObj):
    testName = "Initial state test"
    _printHeader("Test the initial state of the %s object" % lockObj)
    _printInfo("%r Owner %s, expiration time: %s"
               % (lockObj, lockObj.owner, lockObj.expirationTime), 1)
    if lockObj.isLock():
        return False, "%s FAILED" % (testName)
    _printInfo("%r is not lock" % (lockObj), 1)
    if not lockObj.request():
        return False, "%s FAILED" % (testName)
    _printInfo("%r is now lock" % (lockObj), 1)
    if not lockObj.release():
        return False, "%s FAILED" % (testName)
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
                             name='user%d' % (i))
        requestEvents.append(requestEvent)
        accessEvents.append(accessEvent)
        releaseEvents.append(releaseEvent)
        userThreads.append(userThread)
        userThread.start()
    try:
        _printInfo(": Initially owner of %r is %s" % (lockObj, lockObj.owner),
                   1, printLock)
        sendEvent(accessEvents, 0)
        sendEvent(accessEvents, 1)
        _printInfo(": take the lock", 1, printLock)
        sendEvent(requestEvents, 0)
        if not lockObj.isLock() or lockObj.owner != 'user0':
            raise Exception("It shall be lock by user 0")
        sendEvent(accessEvents, 0)
        sendEvent(accessEvents, 1)
        _printInfo(": Try to lock when it is already", 1, printLock)
        sendEvent(requestEvents, 1)
        if not lockObj.isLock() or lockObj.owner != 'user0':
            raise Exception("It shall be lock by user 0")
        sendEvent(accessEvents, 0)
        sendEvent(accessEvents, 1)
        _printInfo(": Try to release by a NON-owner", 1, printLock)
        sendEvent(releaseEvents, 1)
        if not lockObj.isLock() or lockObj.owner != 'user0':
            raise Exception("It shall be lock by user 0")
        sendEvent(accessEvents, 0)
        sendEvent(accessEvents, 1)
        _printInfo(": release the lock")
        sendEvent(releaseEvents, 0)
        if lockObj.isLock():
            raise Exception("It shall be released")
        sendEvent(accessEvents, 0)
        sendEvent(accessEvents, 1)
        _sleep(3)
        # --- here is where the test starts
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
    _printInfo("started", 1, printLock)
    while not joinedEvent.isSet():
        # _printInfo("loop", 1, printLock)
        if request.isSet():
            take = lockObj.request()
            request.clear()
            _printInfo("request %s" % take, 2, printLock)
        if access.isSet():
            if lockObj.isLock():
                _printInfo("rejected to access", 2, printLock)
            else:
                _printInfo("access allowed", 2, printLock)
            access.clear()
        if release.isSet():
            free = lockObj.release()
            release.clear()
            _printInfo("release %s" % free, 2, printLock)
        _sleep(1)
    _printInfo("exit", 1, printLock)


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
