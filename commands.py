###############################################################################
## file :               commands.pyx
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


'''
    This file contains the necessary object to define the tree structure 
    of the scpi commands. From the root to the latest nodes before the leaves 
    they are Component objects that are subclass of dict. the leaves are
    an special type of components that have also the read (and the write 
    optional) for the actions.
'''


from logger import Logger as _Logger
from logger import printHeader


class DictKey(_Logger,str):
    '''
        This class is made to allow the dictionary keys to find a match using 
        the shorter strings allowed in the scpi specs.
    '''
    def __init__(self,value,minimum=4,debug=False,*args,**kargs):
        #super(DictKey,self).__init__(value,minimum,*args,**kargs)
        _Logger.__init__(self,debug)
        str.__init__(value)
        self._name = value
        self._minimum = minimum
        if len(self._name) < self._minimum:
            raise NameError("value string shall be almost the minimum size")
    
    @property
    def minimum(self):
        return self._minimum
    
    @minimum.setter
    def minimum(self,value):
        if type(value) != int:
            raise TypeError("minimum shall be an integer")
        self._minimum = value
    
    def __str__(self):
        return self._name
        
    def __repr__(self):
        return "%s%s"%(self._name[0:self._minimum].upper(),
                       self._name[self._minimum:])
    
    def __eq__(self,other):# => self == other
        '''
            Compare if those two names matches reducing the name until the 
            minimum size.
        '''
        if type(other) == DictKey:
            otherName = other._name.lower()
        elif type(other) == str:
            otherName = other.lower()
        selfName = self._name.lower()
        self._debug("Comparing %s to %s"%(selfName,otherName))
        while len(selfName) >= len(otherName) and \
        len(selfName) >= self._minimum:
            if selfName == otherName:
                self._debug("Found match! %s == %s"%(selfName,otherName))
                return True
            if len(selfName) > self._minimum:
                self._debug("No match found, reducing %s to %s"
                           %(selfName,selfName[:-1]))
            selfName = selfName[:-1]
        return False
    
    def is_(self,other):# => self is other
        return self == other
    
    def __ne__(self,other):# => self != other
        return not self == other
    
    def is_not(self,other):# => not self is other
        return not self is other


class Attribute(DictKey):
    '''
        Leaf node of the scpi command tree
    '''
    def __init__(self,name,read_callback=None,write_callback=None,
                 *args,**kargs):
        #super(Attribute,self).__init__(*args,**kargs)
        DictKey.__init__(self,name,*args,**kargs)
        self._read_callback = read_callback
        self._write_callback = write_callback

    @property
    def read_callback(self):
        return self._read_callback
    
    @read_callback.setter
    def read_callback(self,value):
        self._read_callback = value

    def read(self):
        self._read_callback()
    
    @property
    def write_callback(self):
        return self._write_callback
    
    @write_callback.setter
    def write_callback(self,value):
        self._write_callback = value

    def write(self,value):
        self._write_callback(value)

#TODO: DictKeys that ends with numbers (that represents something like channels
#      shall not include the number in the name and shoud search for 
#      correspondence.

class Component(_Logger,dict):
    '''
        Intermediated nodes of the scpi command tree.
    '''
    def __init__(self,parent=None,debug=False,*args,**kargs):
        #super(Component,self).__init__(debug,*args,**kargs)
        _Logger.__init__(self,debug)
        dict.__init__(self,args,**kargs)
        self._name = dict.get(self,'name_label')
        self._parent = parent
    
    def __repr__(self):
        depth = 0
        parent = self._parent
        while parent != None:
            parent = parent._parent
            depth += 1
        indentation = "\t"*depth
        repr = ""
        for key in self.keys():
            repr = "".join("%s\n%s%r:%r"
                           %(repr,indentation,key,dict.__getitem__(self, key)))
        return repr
    
    def __getitem__(self, key):
        '''
            Given a keyword it checks if it matches, at least the first 
            'minimumkey' characters, with an key in the dictionary to return 
            its content.
        '''
        self._debug("available keywords: %s"%(self.keys()))
        for keyword in self.keys():
            if keyword == key:
                key = keyword
                break
        try:
            val = dict.__getitem__(self, key)
        except:
            raise KeyError("%s not found"%(key))
        self._debug("GET %s['%r'] = %s"
                  %(str(dict.get(self,'name_label')),key,str(val)))
        return val
    
    def __setitem__(self,key,val):
        '''
            The key is case insensitive, then we store it as lower case to 
            compare every where lower cases. Also the key corresponds to any
            substring of it with the minimum size of 'minimumKey'
        '''
        if type(key) != DictKey:
            key = DictKey(key)
        if not type(val) in [Component,Attribute]:
            raise ValueError("dictionary content shall be an attribute "\
                             "or another Component")
        self._debug("SET %s['%r'] = %s"
                   %(str(dict.get(self,'name_label')),key,str(val)))
        dict.__setitem__(self,key,val)


def testDictKey():
    printHeader("Tests for the DictKey object")
    sampleKey = 'qwerty'
    dictKey = DictKey(sampleKey)
    print("Compare the key and it's reduced versions")
    while dictKey == sampleKey:
        print("\t%s == %s"%(dictKey,sampleKey))
        sampleKey = sampleKey[:-1]
    print("\tFinally %s != %s"%(dictKey,sampleKey))


def testComponent():
    #TODO: test channel like Components
    printHeader("Tests for the Component dictionary")
    
    scpitree = Component()
    print("Build a root component: %s"%(scpitree))
    scpitree['rootnode'] = Component(scpitree)
    scpitree['rootnode']['nesteda'] = Attribute('leafa')
    print("Assign a nested component:%s"%(scpitree))
    scpitree['rootnode']['nestedb'] = Attribute('leafb')
    print("Assign another nested component:%s"%(scpitree))
    scpitree['rootnode']['nestedc'] = Component(scpitree['rootnode'])
    scpitree['rootnode']['nestedc']['subnestedc'] = Attribute('leafc')
    print("Assign a double nested component:%s"%(scpitree))


from random import randint
class AttrTest:
    def __init__(self,upperLimit=100,lowerLimit=-100):
        self._upperLimit = upperLimit
        self._lowerLimit = lowerLimit
    def readTest():
        return randint(self._lowerLimit,self._upperLimit)
    @property
    def upperLimit(self):
        return self._upperLimit
    @upperLimit.setter
    def upperLimit(self,value):
        self._upperLimit = value
    @property
    def lowerLimit(self):
        return self._lowerLimit
    @upperLimit.setter
    def lowerLimit(self,value):
        self._lowerLimit = value


def testAttr():
    pass
#    printHeader("Testing read/write operations")
#    
#    scpitree = Component()
#    voltage = AttrTest()
#    #current = AttrTest()
#    scpitree['source'] = Component()
#    scpitree['source']['Voltage'] = Component()
#    #scpitree['source']['voltage'].default()
#    scpitree['source']['voltage'] = Attribute('upper',
#                                             read_callback=voltage.upperLimit,
#                                             write_callback=voltage.upperLimit)
#    scpitree['source']['voltage'] = Attribute('lower',
#                                             read_callback=voltage.lowerLimit,
#                                             write_callback=voltage.lowerLimit)
#    print("%r"%component)


def main():
    for test in [testDictKey,testComponent,testAttr]:
        try:
            test()
        except Exception,e:
            print("Test failed! %s"%e)
            return


if __name__ == '__main__':
    main()