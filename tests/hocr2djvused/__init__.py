# encoding=UTF-8

# Copyright © 2010, 2011 Jakub Wilk <jwilk@jwilk.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

from __future__ import with_statement

import contextlib
import os
import shlex
import sys
from cStringIO import StringIO

from ocrodjvu.cli import hocr2djvused

from tests.common import *

here = os.path.dirname(__file__)
try:
    here = os.path.relpath(here)
except AttributeError:
    # Python 2.5. No big deal.
    pass

def test_help():
    stdout = StringIO()
    stderr = StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(hocr2djvused.main, ['', '--help'])
    assert_equal(rc, 0)
    assert_equal(stderr.getvalue(), '')
    assert_not_equal(stdout.getvalue(), '')

def test_version():
    # http://bugs.debian.org/573496
    stdout = StringIO()
    stderr = StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(hocr2djvused.main, ['', '--version'])
    assert_equal(rc, 0)
    assert_not_equal(stderr.getvalue(), '')
    assert_equal(stdout.getvalue(), '')

def _test_from_file(base_filename, index, extra_args):
    base_filename = os.path.join(here, base_filename)
    test_filename = '%s.test%d' % (base_filename, index)
    html_filename = '%s.html' % (base_filename,)
    with open(test_filename, 'rb') as file:
        commandline = file.readline()
        expected_output = file.read()
    args = shlex.split(commandline) + shlex.split(extra_args)
    assert args[0] == '#'
    with contextlib.closing(StringIO()) as output_file:
        with open(html_filename, 'rb') as html_file:
            with interim(sys, stdin=html_file, stdout=output_file):
                rc = try_run(hocr2djvused.main, args)
        assert_equal(rc, 0)
        output = output_file.getvalue()
    assert_ml_equal(expected_output, output)

def _rough_test_from_file(base_filename, args):
    args = ['#'] + shlex.split(args)
    if base_filename.endswith(('cuneiform0.7', 'cuneiform0.8')):
        # Add dummy page-size information
        args += ['--page-size=1000x1000']
    base_filename = os.path.join(here, base_filename)
    html_filename = '%s.html' % (base_filename,)
    with contextlib.closing(StringIO()) as output_file:
        with open(html_filename, 'rb') as html_file:
            with interim(sys, stdin=html_file, stdout=output_file):
                rc = try_run(hocr2djvused.main, args)
        assert_equal(rc, 0)
        output = output_file.getvalue()
    assert_not_equal(output, '')

def test_from_file():
    rough_test_args = ['--details=lines']
    rough_test_args += [
        '--details=%s%s' % (details, extra)
        for details in ('words', 'chars')
        for extra in ('', ' --word-segmentation=uax29')
    ]
    known_bases = set()
    for test_filename in sorted_glob(os.path.join(here, '*.test[0-9]')):
        index = int(test_filename[-1])
        base_filename = os.path.basename(test_filename[:-6])
        known_bases.add(base_filename)
        for extra_args in '', '--html5':
            yield _test_from_file, base_filename, index, extra_args
    for html_filename in sorted_glob(os.path.join(here, '*.html')):
        # For HTML files that have no corresponing .test* files, we just check
        # if they won't trigger any exception.
        base_filename = os.path.basename(html_filename[:-5])
        for args in rough_test_args:
            if base_filename not in known_bases:
                for extra_args in '', ' --html5':
                    yield _rough_test_from_file, base_filename, args + extra_args

# vim:ts=4 sw=4 et
