# encoding=UTF-8

# Copyright © 2010-2017 Jakub Wilk <jwilk@jwilk.net>
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

from __future__ import unicode_literals
import contextlib
import io
import os
import re
import shlex
import sys

import djvu.sexpr

from lib import errors
from lib.cli import hocr2djvused

from tests.tools import (
    assert_equal,
    assert_multi_line_equal,
    assert_not_equal,
    interim,
    sorted_glob,
    try_run,
)

here = os.path.dirname(__file__)
here = os.path.relpath(here)

def test_help():
    stdout = io.StringIO()
    stderr = io.StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(hocr2djvused.main, ['', '--help'])
    assert_equal(stderr.getvalue(), '')
    assert_equal(rc, 0)
    assert_not_equal(stdout.getvalue(), '')

def test_version():
    # https://bugs.debian.org/573496
    stdout = io.StringIO()
    stderr = io.StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(hocr2djvused.main, ['', '--version'])
    assert_equal(stderr.getvalue(), '')
    assert_equal(rc, 0)
    assert_not_equal(stdout.getvalue(), '')

def test_bad_options():
    stdout = io.StringIO()
    stderr = io.StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(hocr2djvused.main, ['', '--bad-option'])
    assert_equal(rc, errors.EXIT_FATAL)
    assert_not_equal(stderr.getvalue(), '')
    assert_equal(stdout.getvalue(), '')

def normalize_sexpr(match):
    return djvu.sexpr.Expression.from_string(match.group(1)).as_string(width=80)

_djvused_text_re = re.compile('^([(].*)(?=^[.]$)', flags=(re.MULTILINE | re.DOTALL))
def normalize_djvused(script):
    return _djvused_text_re.sub(normalize_sexpr, script)

def _test_from_file(base_filename, index, extra_args):
    base_filename = os.path.join(here, base_filename)
    test_filename = '{base}.test{i}'.format(base=base_filename, i=index)
    html_filename = '{base}.html'.format(base=base_filename)
    with open(test_filename, 'r') as file:
        commandline = file.readline()
        expected_output = file.read()
    args = shlex.split(commandline) + shlex.split(extra_args)
    assert_equal(args[0], '#')
    with contextlib.closing(io.StringIO()) as output_file:
        with open(html_filename, 'r') as html_file:
            with interim(sys, stdin=html_file, stdout=output_file):
                rc = try_run(hocr2djvused.main, args)
        assert_equal(rc, 0)
        output = output_file.getvalue()
    assert_multi_line_equal(
        normalize_djvused(expected_output),
        normalize_djvused(output)
    )

def _rough_test_from_file(base_filename, args):
    args = ['#'] + shlex.split(args)
    if base_filename.endswith(('cuneiform0.7', 'cuneiform0.8')):
        # Add dummy page-size information
        args += ['--page-size=1000x1000']
    base_filename = os.path.join(here, base_filename)
    html_filename = '{base}.html'.format(base=base_filename)
    with contextlib.closing(io.StringIO()) as output_file:
        with open(html_filename, 'r') as html_file:
            with interim(sys, stdin=html_file, stdout=output_file):
                rc = try_run(hocr2djvused.main, args)
        assert_equal(rc, 0)
        output = output_file.getvalue()
    assert_not_equal(output, '')

def test_from_file():
    rough_test_args = ['--details=lines']
    rough_test_args += [
        '--details={0}'.format(details) + extra
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
        # For HTML files that have no corresponding .test* files, we just check
        # if they won't trigger any exception.
        base_filename = os.path.basename(html_filename[:-5])
        for args in rough_test_args:
            if base_filename not in known_bases:
                for extra_args in '', ' --html5':
                    yield _rough_test_from_file, base_filename, args + extra_args

# vim:ts=4 sts=4 sw=4 et
