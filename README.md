# scpi
Python module to provide scpi functionality to an instrument

## Development Status :: 1 - Planning

This code is, by now, only a prove of concept to prepare a python library 
to provide *scpi commands tree* functionality in the **instrument side**.

SCPI library is based on these standards, but *doesn't complain them yet*.
 - [SCPI-99](http://www.ivifoundation.org/docs/scpi-99.pdf)
 - [IEEE 488.2-2004](http://dx.doi.org/10.1109/IEEESTD.2004.95390)
 
## Installation

It has been thought to use setuptools (and someday cython will be introduced 
to have a compiled option to increase performance with long sets of commands).

```
$ python setup.py build
$ python setup.py install --prefix ~
```

The install has been set with a prefix to highlight the current development 
stage and avoid to use in production unless you change it.

## Usage

Different aproaches has been prepared to have instrument side support. The 
most simple shall be to simply build a scpi object in your instrument:

```
import scpi
scpiObj = scpi.scpi()
```

With no paramenter configuration, the object assumes the communication will be
made by network and *only* listen the localhost (in ipv4 and ipv6).

Also, a object created this way doesn't have any command to respond. They can 
be build before and passed to the constructor, or use a command to add:

```
currentObj = AttrTest()
scpiObj.addCommand('source:current:upper',
                   readcb=currentObj.upperLimit,
                   writecb=currentObj.upperLimit)
```

The *AttrTest()* object can be found in the *commands.py* file and it's use 
in the current approach of tests. What the previous code generates are:

* Two nested components, 'source' as root in the scpi command tree,
* 'current' as an intermediate node, and 
* 'upper' a leaf that will be readable and writable.

With this sample code, out object shall be listening on the (loopback) network 
and sending the string 'SOUR:CURR:UPPE?', we will receive back an string with 
the representation of the execution of 'currentObj.upperLimit()'.

## ToDo List

* Components with indexes: channel like components with a numeric tag to 
distinguish between more than one 'signal' source.

* More listen channels than network

* array-like answers

## Other ideas to study

* Event subscription. Unknow if scpi has something about this in the specs.

