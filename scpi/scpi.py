###############################################################################
## file :               scpi.py
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
from version import version as _version

#flags for service activation
TCPLISTENER_LOCAL  = 0b10000000
TCPLISTENER_REMOTE = 0b01000000

def __version__():
    '''Library version with 4 fields: 'a.b.c-d' 
       Where the two first 'a' and 'b' comes from the base C library 
       (scpi-parser), the third is the build of this cypthon port and the last 
       one is a revision number.
    '''
    return _version()

class scpi(_Logger):
    #TODO: build commands
    #TODO: tcpListener
    #TODO: other incomming channels
    def __init__(self,commandTree,services,idn=None,debug=False):
        _Logger.__init__(self,debug=debug)
        self._name = "scpi"
        self._commandTree = commandTree
        self._manufacturerName = None
        self._instrumentName = None
        self._serialNumber = None
        self._firmwareVersion = None
        if idn:
            if type(idn) == list and len(idn) == 4:
                self.manufacturer = idn[0]
                self.instrument = idn[1]
                self.serialNumber = idn[2]
                self.firmwareVersion = idn[3]
            else:
                self._error("Wrongly configured the IDN!")
        self._info("Given commands: %r"%(self._commandTree))
        self._services = {}
        if services & (TCPLISTENER_LOCAL|TCPLISTENER_REMOTE):
            local = services & TCPLISTENER_LOCAL
            self._debug("Opening tcp listener (%s)"
                        %("local" if local else "remote"))
            self._services['tcpListener'] = TcpListener(name="TcpListener",
                                                        parent=self,
                                                        local=local,
                                                        debug=debug)
            self._services['tcpListener'].listen()

    def __del__(self):
        self._info("Delete request received")
        for key,service in self._services.items():
            if hasattr(service,'close'):
                service.close()
            else:
                del service
                
    def input(self,line):
        self._debug("Received '%s' input"%(line))
        line = line.split(';')
        results = []
        for i,command in enumerate(line):
            if command.startswith('*'):
                results.append(self._process_special_command(command[1:]))
            else:
                if command.startswith(':'):
                    if i == 0:
                        self._error("For command '%s': Not possible to start "\
                                    "with ':', without previous command"
                                    %(command))
                        results.append(float('NaN'))
                    else:
                        #populate fields pre-':' 
                        #with the previous (i-1) command
                        command = \
                        "".join("%s%s"%(line[i-1].rsplit(':')[0],command))
                        results.append(self._process_normal_command(command))
                        #results.append(float('NaN'))
                else:
                    results.append(self._process_normal_command(command))
        self._debug("Answers: %s"%(results))
        answer = ""
        for res in results:
            answer = "".join("%s%s;"%(answer,res))
        self._debug("Answer: %s"%(answer))
        return answer
    
    def _process_special_command(self,cmd):
        if cmd.endswith('?'):
            if cmd.lower() == "idn?":
                return self.idn
        #TODO
        self._error("This is an special command, but it's not yet supported")
        return float('NaN')
    def _process_normal_command(self,cmd):
        keywords = cmd.split(':')
        tree = self._commandTree
        for key in keywords:
            self._debug("processing %s"%key)
            try:
                tree = tree[key]
            except:
                if key.endswith('?'):
                    self._debug("last keyword: %s"%(key))
                    try:
                        return tree[key[:-1]].read()
                    except:
                        return float('NaN')
                else:
                    try:
                        bar = key.split(' ')
                        #if there is more than one space in the middle, 
                        #take first and last
                        key = bar[0];value = bar[-1]
                        tree[key].write(value)
                        return tree[key].read()
                    except:
                        return float('NaN')

    @property
    def manufacturer(self):
        return self._manufacturerName
    
    @manufacturer.setter
    def manufacturer(self,value):
        self._manufacturerName = str(value)
        print("IDN: %s"%(self.idn))
    
    @property
    def instrument(self):
        return self._instrumentName
    
    @instrument.setter
    def instrument(self,value):
        self._instrumentName = str(value)
        print("IDN: %s"%(self.idn))
    
    @property
    def serialNumber(self):
        return self._serialNumber
    
    @serialNumber.setter
    def serialNumber(self,value):
        self._serialNumber = str(value)
        print("IDN: %s"%(self.idn))
    
    @property
    def firmwareVersion(self):
        return self._firmwareVersion
    
    @firmwareVersion.setter
    def firmwareVersion(self,value):
        self._firmwareVersion = str(value)
        print("IDN: %s"%(self.idn))
    
    @property
    def idn(self):
        return "%s,%s,%s,%s"%(self.manufacturer,self.instrument,
                              self.serialNumber,self.firmwareVersion)


#---- TEST AREA
from logger import printHeader


def testScpi():
    from commands import testAttr
    printHeader("Testing scpi main class (version %s)"%(_version()))
    commandSet = testAttr(output=False)
    idn = ["ALBA","test",0,'0.0']
    scpiObj = scpi(commandSet,TCPLISTENER_LOCAL,idn=idn,debug=False)
    cmd = "*IDN?"
    print("Instrument identification (%s): %s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:CURR:UPPER?"
    print("Requested upper current limit (%s): %s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOU:CURRRI:UP?"
    print("Requested something that cannot be requested (%s): %s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:CURR:LOWER?"
    print("Requested lower current limit (%s): %s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:CURR:LOWER -50"
    print("Set the current lower limit to -50 (%s), and the answer is: %s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:CURR:LOWER?"
    print("Request again the current lower limit (%s): %s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:VOLT:LOWER?"
    print("Request lower voltage limit (%s): %s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:VOLT:VALU?"
    print("Request voltage value (%s): %s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:VOLT?"
    print("Request voltage using default (%s): %s"%(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:CURR?;SOUR:VOLT?"
    print("Concatenate 2 commands (%s): %s"%(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:CURR?;:VOLT?"
    print("Concatenate and nested commands (%s): %s"%(cmd,scpiObj.input(cmd)))
    #end
    scpiObj.__del__()


def main():
    import traceback
    for test in [testScpi]:
        try:
            test()
        except Exception,e:
            print("Test failed! %s"%e)
            traceback.print_exc()
            return


if __name__ == '__main__':
    main()
