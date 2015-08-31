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
from commands import Component,BuildComponent,BuildAttribute,BuildSpecialCmd
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
    #TODO: other incomming channels than network
    #TODO: %s %r of the object
    def __init__(self,services=TCPLISTENER_LOCAL,commandTree=None,
                 specialCommands=None,debug=False):
        _Logger.__init__(self,debug=debug)
        self._name = "scpi"
        self._commandTree = commandTree or Component()
        self._specialCmds = specialCommands or {}
        self._info("Special commands: %r"%(specialCommands))
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

    def __str__(self):
        return "%r"%(self)
    
    def __repr__(self):
        if self._specialCmds.has_key('idn'):
            return "scpi(%s)"%(self._specialCmds['idn'].read())
        return "scpi()"

    def addSpecialCommand(self,name,readcb,writecb=None):
        '''
            Adds a command '*%s'%(name). If finishes with a '?' mark it will 
            be called the readcb method, else will be the writecb method.
        '''
        name = name.lower()
        if name.startswith('*'):
            name = name[1:]
        if name.endswith('?'):
            if writecb != None:
                raise KeyError("Refusing command %s: looks readonly but has "\
                               "a query character at the end."%(name))
            name = name[:-1]
        if not name.isalpha():
            raise NameError("Not supported other than alphabetical characters")
        if self._specialCmds == None:
            self._specialCmds = {}
        self._debug("Adding special command '*%s'"%(name))
        BuildSpecialCmd(name,self._specialCmds,readcb,writecb)

    def addComponent(self,name,parent=None):
        if name in parent.keys():
            self._debug("component '%s' already exist"%(name))
            return
        self._debug("Adding component '%s' (%s)"%(name,parent))
        BuildComponent(name,parent)
    
    def addAttribute(self,name,parent,readcb,writecb=None,default=False):
        self._debug("Adding attribute '%s' (%s)"%(name,parent))
        BuildAttribute(name,parent,readcb,writecb,default)

    def addCommand(self,FullName,readcb,writecb=None,default=False):
        '''
            adds the command in the structure of [X:Y:]Z composed by Components
            X, Y and as many as ':' separated have. The last one will 
            correspond with an Attribute with at least a readcb for when it's 
            called with a '?' at the end. Or writecb if it's followed by an 
            space and something that can be casted after.
        '''
        if FullName.startswith('*'):
            self.addSpecialCommand(FullName, readcb, writecb)
            return
        nameParts = FullName.split(':')
        self._debug("Prepare to add command %s"%(FullName))
        tree = self._commandTree
        #preprocessing:
        for part in nameParts:
            if len(part) == 0:
                raise NameError("No null names allowed")
        if len(nameParts) > 1:
            for i,part in enumerate(nameParts[:-1]):
                self.addComponent(part,tree)
                tree = tree[part]
        self.addAttribute(nameParts[-1],tree,readcb,writecb,default)

    def input(self,line):
        self._debug("Received '%s' input"%(line))
        line = line.split(';')
        results = []
        for i,command in enumerate(line):
            self._debug("Processing command: '%s'"%(command))
            if command.startswith('*'):
                results.append(self._process_special_command(command[1:]))
            elif command.startswith(':'):
                if i == 0:
                    self._error("For command '%s': Not possible to start "\
                                "with ':', without previous command"
                                %(command))
                    results.append(float('NaN'))
                else:
                    #populate fields pre-':' 
                    #with the previous (i-1) command
                    command = \
                    "".join("%s%s"%(line[i-1].rsplit(':',1)[0],command))
                    self._debug("Command expanded to '%s'"%(command))
                    results.append(self._process_normal_command(command))
            else:
                results.append(self._process_normal_command(command))
        self._debug("Answers: %s"%(results))
        answer = ""
        for res in results:
            answer = "".join("%s%s;"%(answer,res))
        self._debug("Answer: %s"%(answer))
        #FIXME: has the last character to be ';'?
        return answer[:-1]
    
    def _process_special_command(self,cmd):
        #FIXME: ugly
        self._debug("current special keys: %s"%(self._specialCmds.keys()))
        if cmd.count(':') > 0:
            return float('NaN')
        for key in self._specialCmds.keys():
            self._debug("testing key %s ?= %s"%(key,cmd))
            if cmd.lower().startswith(key):
                if cmd.endswith('?'):
                    return self._specialCmds[key].read()
                else:
                    if cmd.count(' ')>0:
                        bar = cmd.split(' ')
                        name = bar[0],value = bar[-1]
                        return self._specialCmds[name].write(value)
                    else:
                        return self._specialCmds[key].write()
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
                        #TODO: support list readings and its conversion to
                        #      '#NMMMMMMMMM...' stream
                        #This may require a DataFormat feature to pack the 
                        #data in bytes, shorts or longs.
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


#---- TEST AREA
from logger import printHeader


class InstrumentIdentification(object):
    def __init__(self,manufacturer,instrument,serialNumber,firmwareVersion):
        object.__init__(self)
        self.manufacturer = manufacturer
        self.instrument = instrument
        self.serialNumber = serialNumber
        self.firmwareVersion = firmwareVersion
        
    @property
    def manufacturer(self):
        return self._manufacturerName
    
    @manufacturer.setter
    def manufacturer(self,value):
        self._manufacturerName = str(value)
    
    @property
    def instrument(self):
        return self._instrumentName
    
    @instrument.setter
    def instrument(self,value):
        self._instrumentName = str(value)
    
    @property
    def serialNumber(self):
        return self._serialNumber
    
    @serialNumber.setter
    def serialNumber(self,value):
        self._serialNumber = str(value)
    
    @property
    def firmwareVersion(self):
        return self._firmwareVersion
    
    @firmwareVersion.setter
    def firmwareVersion(self,value):
        self._firmwareVersion = str(value)
    
    def idn(self):
        return "%s,%s,%s,%s"%(self.manufacturer,self.instrument,
                              self.serialNumber,self.firmwareVersion)


def testScpi():
    from commands import AttrTest
    printHeader("Testing scpi main class (version %s)"%(_version()))
    
    identity = InstrumentIdentification('ALBA','test',0,'0.0')
    #BuildSpecial('IDN',specialSet,identity.idn)
    scpiObj = scpi(TCPLISTENER_LOCAL,debug=True)
    scpiObj.addSpecialCommand('IDN',identity.idn)
    #invalid commands section
    try:
        scpiObj.addCommand(":startswithcolon",readcb=None)
    except NameError,e:
        print("\tNull name test passed")
    except Exception,e:
        print("\tUnexpected kind of exception!")
        return
    try:
        scpiObj.addCommand("double::colons",readcb=None)
    except NameError,e:
        print("\tDouble colon name test passed")
    except Exception,e:
        print("\tUnexpected kind of exception!")
        return
    #valid commands section
    currentObj = AttrTest()
    scpiObj.addCommand('source:current:upper',readcb=currentObj.upperLimit,
                       writecb=currentObj.upperLimit)
    scpiObj.addCommand('source:current:lower',readcb=currentObj.lowerLimit,
                       writecb=currentObj.lowerLimit)
    scpiObj.addCommand('source:current:value',readcb=currentObj.readTest,
                       default=True)
    voltageObj = AttrTest()
    scpiObj.addCommand('source:voltage:upper',readcb=voltageObj.upperLimit,
                       writecb=voltageObj.upperLimit)
    scpiObj.addCommand('source:voltage:lower',readcb=voltageObj.lowerLimit,
                       writecb=voltageObj.lowerLimit)
    scpiObj.addCommand('source:voltage:value',readcb=voltageObj.readTest,
                       default=True)
    print("Command tree build: %r"%(scpiObj._commandTree))
    
    
    print("Launch test:")
    cmd = "*IDN?"
    print("\tInstrument identification (%s):\n\t\t%s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:CURR:UPPER?"
    print("\tRequested upper current limit (%s):\n\t\t%s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOU:CURRRI:UP?"
    print("\tRequested something that cannot be requested (%s):\n\t\t%s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:CURR:LOWER?"
    print("\tRequested lower current limit (%s):\n\t\t%s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:CURR:LOWER -50"
    print("\tSet the current lower limit to -50 (%s), and the answer is:\n\t\t%s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:CURR:LOWER?"
    print("\tRequest again the current lower limit (%s):\n\t\t%s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:VOLT:LOWER?"
    print("\tRequest lower voltage limit (%s):\n\t\t%s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:VOLT:VALU?"
    print("\tRequest voltage value (%s):\n\t\t%s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:VOLT?"
    print("\tRequest voltage using default (%s):\n\t\t%s"%(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:CURR?;SOUR:VOLT?"
    print("\tConcatenate 2 commands (%s):\n\t\t%s"%(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:CURR?;:VOLT?"
    print("\tConcatenate and nested commands (%s):\n\t\t%s"%(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:CURR:LOWE?;:UPPE?"
    print("\tConcatenate and nested commands (%s):\n\t\t%s"%(cmd,scpiObj.input(cmd)))
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
