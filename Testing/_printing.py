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


from threading import currentThread as _current_thread


def print_header(msg):
    print("\n"+"*"*(len(msg)+4)+"\n* "+msg+" *\n"+"*"*(len(msg)+4)+"\n")


def print_footer(msg):
    print("\n*** {} ***\n".format(msg))


def print_info(msg, level=0, lock=None, top=False, bottom=False):
    if lock is None:
        print("{}{}".format("\t"*level, msg))
    else:
        with lock:
            tab = "\t"*level
            msg = "Thread {}: {}".format(_current_thread().name, msg)
            if top or bottom:
                if top:
                    msg = "{}{}\n{}{}".format(tab, "-"*len(msg), tab, msg)
                elif bottom:
                    msg = "{}{}}\n{}{}\n".format(tab, msg, tab, "-"*len(msg))
            else:
                msg = "{}{}".format(tab, msg)
            print(msg)
