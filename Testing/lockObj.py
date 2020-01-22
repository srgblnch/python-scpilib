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

from scpilib.lock import Locker

# --- testing area
from optparse import OptionParser
from _printing import print_header as _print_header
from _printing import print_footer as _print_footer
from _printing import print_info as _print_info
import sys
from time import sleep as _sleep
from threading import currentThread as _currentThread
from threading import Event as _Event
from threading import Lock as _Lock
from threading import Thread as _Thread
from traceback import print_exc


TEST_EXPIRATION_TIME = 10  # seconds


def lock_take(lock_obj):
    test_name = "Initial state test"
    _print_header("Test the initial state of the {} object".format(lock_obj))
    _print_info("{!r}".format(lock_obj), 1)

    _print_info("Check if it is lock", level=1, top=True)
    if lock_obj.isLock():
        return False, "{} FAILED".format(test_name)
    _print_info("{} is not lock".format(lock_obj), level=1, bottom=True)

    _print_info("Check if it lock can be requested", level=1, top=True)
    if not lock_obj.request():
        return False, "{} FAILED".format(test_name)
    _print_info("{!r} is now lock".format(lock_obj), level=1, bottom=True)

    _print_info("Check if it lock can be released", level=1, top=True)
    if not lock_obj.release():
        return False, "{} FAILED".format(test_name)
    _print_info("{!r} is now released".format(lock_obj), level=1, bottom=True)

    return True, "{} PASSED".format(test_name)


def multithreading_take(lock_obj):
    def send_event(event_lst, who):
        event_lst[who].set()
        while event_lst[who].isSet():  # wait to the thread to work
            _sleep(1)
    test_name = "Lock take test"
    _print_header("{} for {}".format(test_name, lock_obj))
    joiner_event = _Event()
    joiner_event.clear()
    user_threads = []
    request_events = []
    access_events = []
    release_events = []
    print_lock = _Lock()
    for i in range(2):
        request_event = _Event()
        access_event = _Event()
        release_event = _Event()
        user_thread = _Thread(target=thread_function,
                              args=(lock_obj, joiner_event,
                                    request_event, access_event, release_event,
                                    print_lock),
                              name='{:d}'.format(i))
        request_events.append(request_event)
        access_events.append(access_event)
        release_events.append(release_event)
        user_threads.append(user_thread)
        user_thread.start()
    # here is where the test starts ---
    try:
        _print_info("Initial state {!r}\n".format(lock_obj),
                    level=1, lock=print_lock)
        if lock_obj.isLock():
            return False, "{} FAILED".format(test_name)

        _print_info("Tell the threads to access",
                    level=1, lock=print_lock, top=True)
        send_event(access_events, 0)
        send_event(access_events, 1)
        _print_info("both should have had access",
                    level=1, lock=print_lock, bottom=True)

        _print_info("Thread 0 take the lock",
                    level=1, lock=print_lock, top=True)
        send_event(request_events, 0)
        if not lock_obj.isLock() or lock_obj.owner != '0':
            raise Exception("It shall be lock by 0")
        _print_info("Tell the threads to access",
                    level=1, lock=print_lock)
        send_event(access_events, 0)
        send_event(access_events, 1)
        _print_info("0 should, but 1 don't",
                    level=1, lock=print_lock, bottom=True)

        _print_info("Try to lock when it is already",
                    level=1, lock=print_lock, top=True)
        send_event(request_events, 1)
        if not lock_obj.isLock() or lock_obj.owner != '0':
            raise Exception("It shall be lock by user 0")
        _print_info("Tell the threads to access",
                    level=1, lock=print_lock)
        send_event(access_events, 0)
        send_event(access_events, 1)
        _print_info("0 should, but 1 don't",
                    level=1, lock=print_lock, bottom=True)

        _print_info("Try to release by a NON-owner",
                    level=1, lock=print_lock, top=True)
        send_event(release_events, 1)
        if not lock_obj.isLock() or lock_obj.owner != '0':
            raise Exception("It shall be lock by user 0")
        _print_info("Tell the threads to access",
                    level=1, lock=print_lock)
        send_event(access_events, 0)
        send_event(access_events, 1)
        _print_info("0 should, but 1 don't",
                    level=1, lock=print_lock, bottom=True)

        _print_info("release the lock",
                    level=1, lock=print_lock, top=True)
        send_event(release_events, 0)
        if lock_obj.isLock():
            raise Exception("It shall be released")
        _print_info("Tell the threads to access",
                    level=1, lock=print_lock)
        send_event(access_events, 0)
        send_event(access_events, 1)
        _print_info("both should have had to",
                    level=1, lock=print_lock, bottom=True)

        # TODO: timeout
        _print_info("Thread 1 take the lock and expire it",
                    level=1, lock=print_lock, top=True)
        send_event(request_events, 1)
        if not lock_obj.isLock() or lock_obj.owner != '1':
            raise Exception("It shall be lock by 1")
        _print_info("Tell the threads to access",
                    level=1, lock=print_lock)
        send_event(access_events, 0)
        send_event(access_events, 1)
        _print_info("1 should, but 0 don't",
                    level=1, lock=print_lock)
        _print_info("Sleep {:d} seconds to expire the lock".format(
            TEST_EXPIRATION_TIME), level=1, lock=print_lock)
        _sleep(TEST_EXPIRATION_TIME)
        _print_info("Tell the threads to access",
                    level=1, lock=print_lock)
        send_event(access_events, 0)
        send_event(access_events, 1)
        _print_info("both should have had to",
                    level=1, lock=print_lock, bottom=True)

        answer = True, "{} PASSED".format(test_name)
    except Exception as e:
        print(e)
        print_exc()
        answer = False, "{} FAILED".format(test_name)
    joiner_event.set()
    while len(user_threads) > 0:
        user_thread = user_threads.pop()
        user_thread.join(1)
        if user_thread.is_alive():
            user_threads.append(user_thread)
    print("All threads has finished")
    return answer


def thread_function(lock_obj, joined_event, request, access, release,
                    print_lock):
    _print_info("started", level=1, lock=print_lock)
    while not joined_event.isSet():
        # _print_info("loop", level=1, lock=print_lock)
        if request.isSet():
            take = lock_obj.request(TEST_EXPIRATION_TIME)
            request.clear()
            _print_info("request {}".format(take), level=2, lock=print_lock)
        if access.isSet():
            if lock_obj.access():
                _print_info("access allowed", level=2, lock=print_lock)
            else:
                _print_info("rejected to access", level=2, lock=print_lock)
            access.clear()
        if release.isSet():
            free = lock_obj.release()
            release.clear()
            _print_info("release {}".format(free), level=2, lock=print_lock)
        _sleep(1)
    _print_info("exit", level=1, lock=print_lock)


def main():
    parser = OptionParser()
    parser.add_option('', "--debug", action="store_true", default=False,
                      help="Set the debug flag")
    (options, args) = parser.parse_args()
    lock_obj = Locker(name='LockerTest', debug=options.debug)
    print("\nBasic locker functionality test:")
    results = []
    messages = []
    for test in [lock_take, multithreading_take]:
        result, msg = test(lock_obj)
        results.append(result)
        messages.append(msg)
        _print_footer(msg)
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
