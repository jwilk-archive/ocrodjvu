#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008, 2009 Jakub Wilk <ubanus@users.sf.net>
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
import sys

from ocrodjvu import hocr
from ocrodjvu import version

__version__ = version.__version__

class ArgumentParser(argparse.ArgumentParser):

    _details_map = dict(
        lines=hocr.TEXT_DETAILS_LINE,
        words=hocr.TEXT_DETAILS_WORD,
        chars=hocr.TEXT_DETAILS_CHARACTER,
    )

    def __init__(self):
        usage = '%(prog)s [options] < <hocr-file> | djvused -s <djvu-file>'
        version = '%(prog) ' + __version__
        argparse.ArgumentParser.__init__(self, usage=usage, version=version)
        self.add_argument('--rotation', dest='rotation', action='store', type=int, default=0, help='page rotation (in degrees)')
        self.add_argument('-t', '--details', dest='details', choices=('lines', 'words', 'chars'), action='store', default='words', help='amount of text details to extract')
        group = self.add_argument_group(title='word segmentation options')
        group.add_argument('--word-segmentation', dest='word_segmentation', choices=('simple', 'uax29'), default='space', help='word segmentation algorithm')
        group.add_argument('--language', dest='language', help='language for word segmentation', default='eng')

    def parse_args(self):
        options = argparse.ArgumentParser.parse_args(self)
        if options.rotation % 90 != 0:
            self.error('Rotation is not a multiple of 90 degrees')
        options.details = self._details_map[options.details]
        options.uax29 = options.language if options.word_segmentation == 'uax29' else None
        del options.word_segmentation
        return options

def main():
    options = ArgumentParser().parse_args()
    for i, text in enumerate(hocr.extract_text(sys.stdin, rotation=options.rotation, details=options.details, uax29=options.uax29)):
        sys.stdout.write('select %d\nremove-txt\nset-txt\n' % (i + 1))
        text.print_into(sys.stdout, 80)
        sys.stdout.write('\n.\n\n')

# vim:ts=4 sw=4 et
