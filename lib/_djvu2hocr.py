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

import argparse

from . import version

__version__ = version.__version__

class ArgumentParser(argparse.ArgumentParser):

    def __init__(self):
        usage = '%(prog)s [options] FILE'
        version = '%(prog) ' + __version__
        argparse.ArgumentParser.__init__(self, usage=usage, version=version)
        self.add_argument('-p', '--pages', dest='pages', action='store', default=None, help='pages to convert')
        self.add_argument('path', metavar='FILE', help='DjVu file to process')

def main():
    options = ArgumentParser().parse_args()
    raise NotImplementedError

# vim:ts=4 sw=4 et
