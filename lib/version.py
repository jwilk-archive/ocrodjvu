# encoding=UTF-8

# Copyright © 2016 Jakub Wilk <jwilk@jwilk.net>
#
# This file is part of ocrodjvu.
#
# ocrodjvu is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# ocrodjvu is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
# for more details.

from __future__ import print_function

import argparse
import sys

__version__ = '0.11'

class VersionAction(argparse.Action):
    '''
    argparse --version action
    '''

    def __init__(self, option_strings, dest=argparse.SUPPRESS):
        super(VersionAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            help="show program's version information and exit"
        )

    def __call__(self, parser, namespace, values, option_string=None):
        print('{prog} {0}'.format(__version__, prog=parser.prog))
        print('+ Python {0}.{1}.{2}'.format(*sys.version_info))
        if 'subprocess32' in sys.modules:
            print('+ subprocess32')
        try:
            djvu_decode = sys.modules['djvu.decode']
        except LookupError:  # no coverage
            pass
        else:
            print('+ python-djvulibre {0}'.format(djvu_decode.__version__))
        try:
            lxml_etree = sys.modules['lxml.etree']
        except LookupError:  # no coverage
            pass
        else:
            print('+ lxml {0}'.format(lxml_etree.__version__))
        try:
            import html5lib
        except ImportError:  # no coverage
            pass
        else:
            print('+ html5lib-python {0}'.format(html5lib.__version__))
        try:
            from . import unicode_support
            pyicu = unicode_support.get_icu()
        except ImportError:  # no coverage
            pass
        else:
            print('+ PyICU {0}'.format(pyicu.VERSION))
            print('  + ICU {0}'.format(pyicu.ICU_VERSION))
            print('    + Unicode {0}'.format(pyicu.UNICODE_VERSION))
        parser.exit()

__all__ = [
    'VersionAction',
    '__version__',
]

# vim:ts=4 sts=4 sw=4 et
