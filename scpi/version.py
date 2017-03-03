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

__author__ = "Sergi Blanch-Torne"
__email__ = "sblanch@cells.es"
__copyright__ = "Copyright 2015, CELLS / ALBA Synchrotron"
__license__ = "GPLv3+"

# Look at https://en.wikipedia.org/wiki/Software_versioning

_MAJOR_VERSION = 0
_MIDDLE_VERSION = 3
_MINOR_VERSION = 4
_BUILD_VERSION = 3

def VERSION():
    return (_MAJOR_VERSION, _MIDDLE_VERSION,
            _MINOR_VERSION, _BUILD_VERSION)


def version():
    return '%d.%d.%d-%d' % (_MAJOR_VERSION, _MIDDLE_VERSION,
                            _MINOR_VERSION, _BUILD_VERSION)
