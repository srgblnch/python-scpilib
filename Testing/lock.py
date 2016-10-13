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
__copyright__ = "Copyright 2016, CELLS / ALBA Synchrotron"
__license__ = "GPLv3+"

from scpi.lock import Locker

# --- testing area
from optparse import OptionParser
try:
    from .printing import printHeader as _printHeader
    from .printing import printFooter as _printFooter
except:
    from printing import printHeader as _printHeader
    from printing import printFooter as _printFooter
import sys
from time import sleep as _sleep
from threading import currentThread as _currentThread
from threading import Event as _Event
from threading import Lock as _Lock
from threading import Thread as _Thread
from traceback import print_exc


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
    if all(results):
        sys.exit(0)
    else:
        sys.exit(-1)


if __name__ == '__main__':
    main()