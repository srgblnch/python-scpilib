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

from setuptools import setup, find_packages

__author__ = "Sergi Blanch-Torne"
__email__ = "sblanch@cells.es"
__copyright__ = "Copyright 2015, CELLS / ALBA Synchrotron"
__license__ = "GPLv3+"

__project__ = 'scpilib'
__description__ = "Python module to provide scpi functionality "\
                  "from instrument side"
__longDesc__ = """
This module has been prepared to provide an instrument the functionality
to be accessed via the SCPI Protocol.

By now it only supports network connection, by default port 5025.
"""
__url__ = "https://github.com/srgblnch/python-scpilib"
# we use semantic versioning (http://semver.org/) and we update it using the
# bumpversion script (https://github.com/peritus/bumpversion)
__version__ = '0.4.0'


setup(name=__project__,
      license=__license__,
      description=__description__,
      long_description=__longDesc__,
      version=__version__,
      author=__author__,
      author_email=__email__,
      classifiers=['Development Status :: 2 - Pre-Alpha',
                   'Intended Audience :: Developers',
                   'Intended Audience :: Science/Research',
                   'License :: OSI Approved :: '
                   'GNU General Public License v3 or later (GPLv3+)',
                   'Operating System :: POSIX',
                   'Programming Language :: Python',
                   'Topic :: Scientific/Engineering :: '
                   'Interface Engine/Protocol Translator',
                   'Topic :: Software Development :: Embedded Systems',
                   'Topic :: Software Development :: Libraries :: '
                   'Python Modules',
                   'Topic :: System :: Hardware',
                   ],
      packages=find_packages(),
      url=__url__,
      )

# for the classifiers review see:
# https://pypi.python.org/pypi?%3Aaction=list_classifiers
#
# Development Status :: 1 - Planning
# Development Status :: 2 - Pre-Alpha
# Development Status :: 3 - Alpha
# Development Status :: 4 - Beta
# Development Status :: 5 - Production/Stable
