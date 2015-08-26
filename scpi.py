###############################################################################
## file :               scpi.pyx
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
## You should have received a copy of the GNU General Public License
## along with Tango.  If not, see <http:##www.gnu.org/licenses/>.
##
###############################################################################


#include "commands.py"
from commands import DictKey,Component,Attribute
#include "logger.py"
from logger import Logger as _Logger
#include "tcpListener.py"
from tcpListener import TcpListener
#include "version.py"


def __version__():
    '''Library version with 4 fields: 'a.b.c-d' 
       Where the two first 'a' and 'b' comes from the base C library 
       (scpi-parser), the third is the build of this cypthon port and the last 
       one is a revision number.
    '''
    return version.version()

class scpi(_Logger):
    #TODO: build commands
    #TODO: tcpListener
    #TODO: other incomming channels
    pass

def main():
    from commands import main as commandsTest
    for test in [commandsTest]:
        try:
            test()
        except Exception,e:
            print("Test failed! %s"%e)
            return


if __name__ == '__main__':
    main()