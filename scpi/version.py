###############################################################################
## file :               version.py
##
## description :        Python module to provide scpi functionality to an 
##                      instrument.
##
## project :            scpi
##
## author(s) :          S.Blanch-Torn\'e
##
## Copyright (C) :      2015
##                      CELLS / ALBA Synchrotron,
##                      08290 Bellaterra,
##                      Spain
##
## This file is part of Tango.
##
## Tango is free software: you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## Tango is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with Tango.  If not, see <http:##www.gnu.org/licenses/>.
##
###############################################################################

#Look at https://en.wikipedia.org/wiki/Software_versioning

__MAJOR_VERSION = 0
__MINOR_VERSION = 1
__BUILD_VERSION = 0
__REVISION_VERSION = 0
__RELEASE_CANDIDATE = None


def version():
    if __RELEASE_CANDIDATE:
        return "%d.%d-rc%d"%(__MAJOR_VERSION,__MINOR_VERSION,
                             __RELEASE_CANDIDATE)
    else:
        return "%d.%d.%d-%d"%(__MAJOR_VERSION,__MINOR_VERSION,
                              __BUILD_VERSION,__REVISION_VERSION)