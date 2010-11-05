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

import sys
from cStringIO import StringIO

from ocrodjvu.cli import ocrodjvu

from tests.common import *

engines = None

def test_help():
    stdout = StringIO()
    stderr = StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(ocrodjvu.main, ['', '--help'])
    assert_equal(rc, 0)
    assert_equal(stderr.getvalue(), '')
    assert_not_equal(stdout.getvalue(), '')

def test_version():
    # http://bugs.debian.org/573496
    stdout = StringIO()
    stderr = StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(ocrodjvu.main, ['', '--version'])
    assert_equal(rc, 0)
    assert_not_equal(stderr.getvalue(), '')
    assert_equal(stdout.getvalue(), '')

def test_list_engines():
    global engines
    stdout = StringIO()
    stderr = StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(ocrodjvu.main, ['', '--list-engines'])
    assert_equal(rc, 0)
    assert_equal(stderr.getvalue(), '')
    engines = stdout.getvalue().splitlines()

def _test_list_languages(engine):
    stdout = StringIO()
    stderr = StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(ocrodjvu.main, ['', '--ocr-engine', engine, '--list-languages'])
    assert_equal(rc, 0)
    assert_equal(stderr.getvalue(), '')
    assert_not_equal(stdout.getvalue(), '')

def test_list_languages():
    assert_true(engines is not None)
    for engine in engines:
        yield _test_list_languages, engine

# vim:ts=4 sw=4 et
