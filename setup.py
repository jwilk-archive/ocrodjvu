#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2009 Jakub Wilk <ubanus@users.sf.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

'''
*ocrodjvu* is a wrapper for `OCRopus <http://ocropus.googlecode.com/>`_, an OCR system, that allows you to perform OCR on `DjVu <http://djvu.org/>`_ files.
'''

import os
os.putenv('TAR_OPTIONS', '--owner root --group root --mode a+rX')

classifiers = '''\
Development Status :: 4 - Beta
Environment :: Console
Intended Audience :: End Users/Desktop
License :: OSI Approved :: GNU General Public License (GPL)
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 2
Topic :: Text Processing
Topic :: Multimedia :: Graphics\
'''.split('\n')

from distutils.core import setup
from lib.ocrodjvu import version

setup(
    name = 'ocrodjvu',
    version = version.__version__,
    license = 'GNU GPL 2',
    description = 'OCRopus for DjVu',
    long_description = __doc__.strip(),
    classifiers = classifiers,
    url = 'http://jwilk.net/software/ocrodjvu.html',
    author = 'Jakub Wilk',
    author_email = 'ubanus@users.sf.net',
    packages = ['ocrodjvu'],
    package_dir = dict(ocrodjvu = 'lib'),
    scripts = ['ocrodjvu', 'hocr2djvused', 'djvu2hocr'],
)

# vim:ts=4 sw=4 et
