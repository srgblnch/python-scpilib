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


import atexit
try:
    from .commands import Component, BuildComponent, BuildChannel,\
                          BuildAttribute, BuildSpecialCmd, AttrTest
    from .logger import Logger as _Logger
    from .tcpListener import TcpListener
    from .version import version as _version
except:
    from commands import Component, BuildComponent, BuildChannel,\
                         BuildAttribute, BuildSpecialCmd, AttrTest
    from logger import Logger as _Logger
    from tcpListener import TcpListener
    from version import version as _version
from time import sleep as _sleep

from threading import currentThread as _currentThread

#DEPRECATED: flags for service activation
TCPLISTENER_LOCAL  = 0b10000000
TCPLISTENER_REMOTE = 0b01000000


global scpiObjects
scpiObjects = []

@atexit.register
def doOnExit():
    for obj in scpiObjects:
        obj.close()


def __version__():
    '''Library version with 4 fields: 'a.b.c-d' 
       Where the two first 'a' and 'b' comes from the base C library 
       (scpi-parser), the third is the build of this cypthon port and the last 
       one is a revision number.
    '''
    return _version()

class scpi(_Logger):
    '''This is an object to be build in order to provide to your instrument
       SCPI communications. By now it only provides network (ipv4 and ipv6)
       communications, but if required it can be extended to support other
       types.
       
       By default it builds sockets that only listen in the loopback network 
       interface. By default we like to avoid to expose the conection. There
       are two ways to allow direct remote connections. One in the constructor
       by calling it with the parameter services=TCPLISTENER_REMOTE. The other
       can be called once the object is created by setting the object property
       'remoteAllowed' to True.
       
       
    '''
    #TODO: other incomming channels than network
    #TODO: %s %r of the object
    def __init__(self,commandTree=None,specialCommands=None,
                 local=True,port=5025,autoOpen=False,debug=False,
                 services=None):
        super(scpi,self).__init__(debug=debug)
        self._name = "scpi"
        self._commandTree = commandTree or Component()
        self._specialCmds = specialCommands or {}
        self._info("Special commands: %r"%(specialCommands))
        self._info("Given commands: %r"%(self._commandTree))
        self._local = local
        self._port = port
        self._services = {}
        if not services == None:
            msg = "The argument 'services' is deprecated, "\
                  "please use the boolean 'local'"
            header = "*"*len(msg)
            print("%s\n%s\n%s"%(header,msg,header))
            if services & (TCPLISTENER_LOCAL|TCPLISTENER_REMOTE):
                self._local = bool(services & TCPLISTENER_LOCAL)
        if autoOpen:
            self.open()
        scpiObjects.append(self)

    #TODO: status information method 
    #(report the open listeners and accepted connections ongoing).

    def __enter__(self):
        self._debug("received a enter() request")
        if not self.isOpen:
            self.open()
        return self
 
    def __exit__(self,type, value, traceback):
        self._debug("received a exit(%s,%s,%s) request"
                    %(type, value, traceback))
        self.__del__()
        

    def __del__(self):
        self._debug("Delete request received")
        if self.isOpen:
            if scpiObjects.count(self):
                scpiObjects.pop(scpiObjects.index(self))
            self.close()

    def __str__(self):
        return "%r"%(self)

    def __repr__(self):
        if self._specialCmds.has_key('idn'):
            return "scpi(%s)"%(self._specialCmds['idn'].read())
        return "scpi()"

    @property
    def isOpen(self):
        return any([self._services[key].isListening() \
                    for key in self._services.keys()])

    def open(self):
        self.__buildTcpListener()

    def close(self):
        for key in self._services.keys():
            self._services[key].close()

    def __buildTcpListener(self):
        self._debug("Opening tcp listener (%s)"
                    %("local" if self._local else "remote"))
        self._services['tcpListener'] = TcpListener(name="TcpListener",
                                                    callback=self.input,
                                                    local=self._local,
                                                    port=self._port,
                                                    debug=self._debugFlag)
        self._services['tcpListener'].listen()

    @property
    def remoteAllowed(self):
        return not self._services['tcpListener']._local

    @remoteAllowed.setter
    def remoteAllowed(self,value):
        if type(value) != bool:
            raise AssertionError("Only boolean can be assigned")
        if value != (not self._services['tcpListener']._local):
            tcpListener = self._services.pop('tcpListener')
            tcpListener.close()
            self._debug("Close the active listeners and their connections.")
            while tcpListener.isListening():
                self._warning("Waiting for listerners finish")
                _sleep(1)
            self._debug("Building the new listeners.")
            if value == True:
                self.__buildTcpListener(TCPLISTENER_REMOTE)
            else:
                self.__buildTcpListener(TCPLISTENER_LOCAL)
        else:
            self._debug("Nothing to do when setting like it was.")

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

    @property
    def specialCommands(self):
        return self._specialCmds.keys()

    def addComponent(self,name,parent):
        if not hasattr(parent,'keys'):
            raise TypeError("For %s, parent doesn't accept components"%(name))
        if name in parent.keys():
            self._debug("component '%s' already exist"%(name))
            return
        self._debug("Adding component '%s' (%s)"%(name,parent))
        return BuildComponent(name,parent)

    def addChannel(self,name,howMany,parent):
        if not hasattr(parent,'keys'):
            raise TypeError("For %s, parent doesn't accept components"%(name))
        if name in parent.keys():
            self._debug("component '%s' already exist"%(name))
            return
        self._debug("Adding component '%s' (%s)"%(name,parent))
        return BuildChannel(name,howMany,parent)

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
        for i,part in enumerate(nameParts):
            if len(part) == 0:
                raise NameError("No null names allowed "\
                                "(review element %d of %s)"%(i,FullName))
        if len(nameParts) > 1:
            for i,part in enumerate(nameParts[:-1]):
                self.addComponent(part,tree)
                tree = tree[part]
        self.addAttribute(nameParts[-1],tree,readcb,writecb,default)

    @property
    def commands(self):
        return self._commandTree.keys()

    def input(self,line):
        self._debug("Received %r input"%(line))
        while len(line) > 0 and line[-1] in ['\r','\n',';']:
            self._debug("from %r remove %r"%(line,line[-1]))
            line = line[:-1]
        if len(line) == 0:
            return ''
        line = line.split(';')
        results = []
        for i,command in enumerate(line):
            command = command.strip()#avoid '\n' terminator if exist
            self._debug("Processing %dth command: %r"%(i+1,command))
            if command.startswith('*'):
                results.append(self._process_special_command(command[1:]))
            elif command.startswith(':'):
                if i == 0:
                    self._error("For command %r: Not possible to start "\
                                "with ':', without previous command"
                                %(command))
                    results.append(float('NaN'))
                else:
                    #populate fields pre-':' 
                    #with the previous (i-1) command
                    command = \
                    "".join("%s%s"%(line[i-1].rsplit(':',1)[0],command))
                    self._debug("Command expanded to %r"%(command))
                    results.append(self._process_normal_command(command))
            else:
                results.append(self._process_normal_command(command))
        self._debug("Answers: %r"%(results))
        answer = ""
        for res in results:
            answer = "".join("%s%s;"%(answer,res))
        self._debug("Answer: %r"%(answer))
        #FIXME: has the last character to be ';'?
        return answer[:-1]+'\r\n'
    
    def _process_special_command(self,cmd):
        #FIXME: ugly
        self._debug("current special keys: %s"%(self._specialCmds.keys()))
        if cmd.count(':') > 0:#Not expected in special commands
            return float('NaN')
        for key in self._specialCmds.keys():
            self._debug("testing key %s ?= %s"%(key,cmd))
            if cmd.lower().startswith(key.lower()):
                if cmd.endswith('?'):
                    self._debug("Requesting read of %s"%(key))
                    return self._specialCmds[key].read()
                else:
                    if cmd.count(' ')>0:
                        bar = cmd.split(' ')
                        name = bar[0],value = bar[-1]
                        self._debug("Requesting write of %s with value %s"
                                    %(name,value))
                        return self._specialCmds[name].write(value)
                    else:
                        self._debug("Requesting write of %s without value"
                                    %(key))
                        return self._specialCmds[key].write()
        self._warning("Command (%s) not found..."%(cmd))
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
try:
    from .logger import printHeader
except:
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
    #---- BuildSpecial('IDN',specialSet,identity.idn)
    with scpi(local=True,debug=True) as scpiObj:
        checkIDN(scpiObj, identity)
        checkValidCommands(scpiObj)
        checkCommandExec(scpiObj)
        checkChannels(scpiObj)


def checkIDN(scpiObj, identity):
    scpiObj.addSpecialCommand('IDN',identity.idn)
    #---- invalid commands section
    try:
        scpiObj.addCommand(":startswithcolon",readcb=None)
    except NameError as e:
        print("\tNull name test passed")
    except Exception as e:
        print("\tUnexpected kind of exception!")
        return
    try:
        scpiObj.addCommand("double::colons",readcb=None)
    except NameError as e:
        print("\tDouble colon name test passed")
    except Exception as e:
        print("\tUnexpected kind of exception!")
        return


def checkValidCommands(scpiObj):
    #---- valid commands section
    currentObj = AttrTest()
    voltageObj = AttrTest()
    # * commands can de added by telling their full name:
    scpiObj.addCommand('source:current:upper',readcb=currentObj.upperLimit,
                       writecb=currentObj.upperLimit)
    scpiObj.addCommand('source:current:lower',readcb=currentObj.lowerLimit,
                       writecb=currentObj.lowerLimit)
    scpiObj.addCommand('source:current:value',readcb=currentObj.readTest,
                       default=True)
    scpiObj.addCommand('source:voltage:upper',readcb=voltageObj.upperLimit,
                       writecb=voltageObj.upperLimit)
    scpiObj.addCommand('source:voltage:lower',readcb=voltageObj.lowerLimit,
                       writecb=voltageObj.lowerLimit)
    scpiObj.addCommand('source:voltage:value',readcb=voltageObj.readTest,
                       default=True)
    # * They can be also created in an iterative way
    baseCmdName = 'basicloop'
    for (subCmdName,subCmdObj) in [('current',currentObj),
                                   ('voltage',voltageObj)]:
        for (attrName,attrFunc) in [('upper','upperLimit'),
                                    ('lower','LowerLimit'),
                                    ('value','readTest')]:
            if hasattr(subCmdObj,attrFunc):
                cbFunc = getattr(subCmdObj,attrFunc)
                if attrName == 'value':
                    default=True
                else:
                    default=False
                scpiObj.addCommand('%s:%s:%s'
                                   %(baseCmdName,subCmdName,attrName),
                                   readcb=cbFunc,default=default)
                #Basically is the same than the first example, but the
                #addCommand is constructed with variables in neasted loops
    # * Another alternative to create the tree in an iterative way would be
    itCmd = 'iterative'
    itObj = scpiObj.addComponent(itCmd,scpiObj._commandTree)
    for subcomponent in ['current','voltage']:
        subcomponentObj = scpiObj.addComponent(subcomponent,itObj)
        for (attrName,attrFunc) in [('upper','upperLimit'),
                                    ('lower','LowerLimit'),
                                    ('value','readTest')]:
            if hasattr(subcomponentObj,attrFunc):
                cbFunc = getattr(subcomponentObj,attrFunc)
                if attrName == 'value':
                    default=True
                else:
                    default=False
                scpiObj.addAttribute(attrName,subcomponentObj,cbFunc,
                                     default=default)
                #In this case, the intermediate objects of the tree are
                #build and it is in the innier loop where they have the 
                #attributes created.
                # * Use with very big care this option because the library
                # * don't guarantee that all the branches of the tree will
                # * have the appropiate leafs.


def checkCommandExec(scpiObj):
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
    print("\tSet the current lower limit to -50 (%s), "\
          "and the answer is:\n\t\t%s"
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
    print("\tRequest voltage using default (%s):\n\t\t%s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:CURR?;SOUR:VOLT?"
    print("\tConcatenate 2 commands (%s):\n\t\t%s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:CURR?;:VOLT?"
    print("\tConcatenate and nested commands (%s):\n\t\t%s"
          %(cmd,scpiObj.input(cmd)))
    cmd = "SOUR:CURR:LOWE?;:UPPE?"
    print("\tConcatenate and nested commands (%s):\n\t\t%s"
          %(cmd,scpiObj.input(cmd)))
    #end


def checkChannels(scpiObj):
    chCmd = 'channel'
    chObj = scpiObj.addChannel(chCmd,4,scpiObj._commandTree)
    for subcomponent in ['current','voltage']:
        subcomponentObj = scpiObj.addComponent(subcomponent,chObj)
        for (attrName,attrFunc) in [('upper','upperLimit'),
                                    ('lower','LowerLimit'),
                                    ('value','readTest')]:
            if hasattr(subcomponentObj,attrFunc):
                cbFunc = getattr(subcomponentObj,attrFunc)
                if attrName == 'value':
                    default=True
                else:
                    default=False
                scpiObj.addAttribute(attrName,subcomponentObj,cbFunc,
                                     default=default)
    # TODO: channels with channels until the attributes

def main():
    import traceback
    for test in [testScpi]:
        try:
            test()
        except Exception as e:
            msg = "Test failed!"
            border = "*"*len(msg)
            msg = "%s\n%s:\n%s"%(border,msg,e)
            print(msg)
            traceback.print_exc()
            print(border)
            return


if __name__ == '__main__':
    main()
