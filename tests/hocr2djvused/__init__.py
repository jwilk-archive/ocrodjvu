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

here = os.path.relpath(os.path.dirname(__file__))

def test_help():
    stdout = StringIO()
    stderr = StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(hocr2djvused.main, ['', '--help'])
    assert_equal(rc, 0)
    assert_equal(stderr.getvalue(), '')
    assert_not_equal(stdout.getvalue(), '')

def _test_from_file(base_filename, index):
    base_filename = os.path.join(here, base_filename)
    test_filename = '%s.test%d' % (base_filename, index)
    html_filename = '%s.html' % (base_filename,)
    with open(test_filename, 'rb') as file:
        commandline = file.readline()
        expected_output = file.read()
    args = shlex.split(commandline)
    assert args[0] == '#'
    with contextlib.closing(StringIO()) as output_file:
        with open(html_filename, 'rb') as html_file:
            with interim(sys, stdin=html_file, stdout=output_file):
                rc = try_run(hocr2djvused.main, args)
        assert_equal(rc, 0)
        output = output_file.getvalue()
    assert_ml_equal(output, expected_output)

def test_from_file():
    for test_filename in glob.glob(os.path.join(here, '*.test[0-9]')):
        index = int(test_filename[-1])
        base_filename = os.path.basename(test_filename[:-6])
        yield _test_from_file, base_filename, index

# vim:ts=4 sw=4 et
