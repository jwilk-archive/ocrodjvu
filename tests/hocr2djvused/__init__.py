# encoding=UTF-8
# Copyright © 2010 Jakub Wilk <jwilk@jwilk.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

from __future__ import with_statement

import contextlib
import glob
import os
import re
import shlex
import sys
from cStringIO import StringIO

from ocrodjvu.cli import hocr2djvused

from tests.common import *

def do(test_filename, html_filename, index):
    with open(test_filename, 'rb') as file:
        commandline = file.readline()
        expected_output = file.read()
    args = shlex.split(commandline)
    assert args[0] == '#'
    with contextlib.closing(StringIO()) as output_file:
        with open(html_filename, 'rb') as html_file:
            with interim(sys, stdin=html_file, stdout=output_file):
                hocr2djvused.main(args)
        output = output_file.getvalue()
    assert_ml_equal(output, expected_output)

def list_tests():
    for test_filename in glob.glob(os.path.join(os.path.dirname(__file__), '*.test[0-9]')):
        index = int(test_filename[-1])
        base_filename = test_filename[:-6]
        html_filename = base_filename + '.html'
        func_name = 'test_%s_t%d' % (re.sub(r'\W+', '_', os.path.basename(base_filename)), index)
        def func(test_filename=test_filename, html_filename=html_filename, index=index):
            do(test_filename, html_filename, index)
        func.__name__ = func_name
        yield func_name, func

globals().update(dict(list_tests()))

del list_tests

# vim:ts=4 sw=4 et
