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
from traceback import print_exc


DEFAULT_EXPIRATION_TIME = 10  # seconds
UPPER_LIMIT_EXPIRATION_TIME = _timedelta(0, DEFAULT_EXPIRATION_TIME*10, 0)


class Locker(_Logger):
    def __init__(self, *args, **kargs):
        super(Locker, self).__init__(*args, **kargs)
        self._owner = None
        self._when = None
        self._expiration = _timedelta(0, DEFAULT_EXPIRATION_TIME, 0)

    @property
    def owner(self):
        return self._owner

    def Owner(self):
        return self.owner

    def release(self, who):
        if who is not None and self._owner == who:
            self._debug("%s releases the lock" % self._owner)
            self._owner = None
            return True
        else:
            self._error("%s CANNOT release %s's lock" % (who, self._owner))
            return False

    def _forceRelease(self):
        self._warning("Locker forced to be released!")
        self._owner = None
        self._when = None

    def request(self, who, timeout=None):
        if who is None:
            self._warning("To take the lock, one has to provide an "
                          "identification.")
            return False
        self.hasExpired(who)
        if self._owner is None:
            self._owner = who
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
                       % (self._owner, self.expirationTime))
            return True
        return False

    def isLock(self, whoIsAsking=None):
        if self._owner is None:
            self._debug("There is no owner of the lock, %s can pass"
                        % whoIsAsking)
            return False
        # if who is asking if in fact the owner of the lock, it has the right
        # to pass. And the watchdog feature will renew its timeout.
        if self._owner == whoIsAsking:
            self._when = _datetime.now()
            self._debug("The owner is who is asking (%s), "
                        "renew the its booking" % (whoIsAsking))
            return False
        # when someone else ask if the lock allows it to pass, it has to be
        # checked if the owner has overcome its expiration time.
        return not self.hasExpired(whoIsAsking)

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

    def hasExpired(self, whoIsAsking=None):
        if self._when is None:
            self._debug("No expiration time set")
            return True
        delta = _datetime.now() - self._when
        if delta > self._expiration:
            self._info("No news from the lock owner (%s) after %s: release "
                       "the lock%s."
                       % (self._owner, delta,
                          " triggered by the pass request of %s" % whoIsAsking
                          if whoIsAsking else ""))
            self._owner = None
            self._when = None
            return True
        self._debug("lock not expired, still %s for %s" % (delta, self._owner))
        return False


# --- testing area


def printHeader(msg):
    print("*"*(len(msg)+4))
    print("* %s *" % msg)
    print("*"*(len(msg)+4))


def printInfo(msg, level=0):
    print("%s%s" % ("\t"*level, msg))


def printTail(msg):
    print("\n%s %s %s\n" % ("*"*3, msg, "*"*3))


def initialState(lockObj):
    testName = "Initial state test"
    printHeader("Test the initial state of the lock object")
    printInfo("Owner %s, expiration time: %s"
              % (lockObj.owner, lockObj.expirationTime), 1)
    if lockObj.isLock():
        return False, "%s FAILED" % (testName)
    if lockObj.request(None):
        return False, "%s FAILED" % (testName)
    if lockObj.release(None):
        return False, "%s FAILED" % (testName)
    return True, "%s PASSED" % (testName)


def singleUser(lockObj):
    testName = "Single user test"
    printHeader("Test single user")
    requester = 'requester'
    # --- request
    if not lockObj.request(requester):
        return False, "%s FAILED" % (testName)
    printInfo("%s succeed in the request" % requester, 1)
    # --- owner
    if lockObj.owner != requester:
        return False, "%s FAILED" % (testName)
    printInfo("lock owner %s == %s" % (lockObj.owner, requester), 1)
    # --- pass the lock
    if not lockObj.isLock(None):
        return False, "%s FAILED" % (testName)
    printInfo("non-owner cannot pass the lock", 1)
    if lockObj.isLock(requester):
        return False, "%s FAILED" % (testName)
    printInfo("owner can pass the lock", 1)
    # --- release
    if not lockObj.release(requester):
        return False, "%s FAILED" % (testName)
    printInfo("owner release the lock", 1)
    if lockObj.isLock(None):
        return False, "%s FAILED" % (testName)
    printInfo("anyone can pass the lock", 1)
    return True, "%s PASSED" % (testName)


def multiUser(lockObj):
    testName = "multiple users test"
    printHeader("Test multiple users")
    requester1, requester2 = 'requester1', 'requester2'
    # --- request
    if not lockObj.request(requester1):
        return False, "%s FAILED" % (testName)
    printInfo("%s succeed in the request" % (requester1), 1)
    if lockObj.request(requester2):
        return False, "%s FAILED" % (testName)
    printInfo("%s cannot take the lock" % (requester2), 1)
    # --- timeout
    printInfo("wait %s for lock expiration" % lockObj.expirationTime, 1)
    _sleep(lockObj.expirationTime.seconds+1)
    if not lockObj.request(requester2, 10):
        return False, "%s FAILED" % (testName)
    printInfo("%s timeout release, %s succeed in the request"
              % (requester1, requester2), 1)
    return True, "%s PASSED" % (testName)


def main():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('', "--debug", action="store_true", default=False,
                      help="Set the debug flag")
    (options, args) = parser.parse_args()
    lockObj = Locker(debug=options.debug)
    print("\nBasic locker functionality test:")
    results = []
    messages = []
    for test in [initialState, singleUser, multiUser]:
        result, msg = test(lockObj)
        results.append(result)
        messages.append(msg)
        printTail(msg)
    if all(results):
        print("All tests PASSED")
    else:
        print("ALERT! NOT ALL THE TESTS HAS PASSED. Check the list")
    for msg in messages:
        print(msg)


if __name__ == '__main__':
    main()
