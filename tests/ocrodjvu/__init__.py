# encoding=UTF-8

# Copyright © 2010-2015 Jakub Wilk <jwilk@jwilk.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

import io
import sys

from lib.cli import ocrodjvu

from tests.common import (
    assert_equal,
    assert_is_not_none,
    assert_not_equal,
    interim,
    try_run,
)

engines = None

def test_help():
    stdout = io.BytesIO()
    stderr = io.BytesIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(ocrodjvu.main, ['', '--help'])
    assert_equal(rc, 0)
    assert_equal(stderr.getvalue(), '')
    assert_not_equal(stdout.getvalue(), '')

def test_version():
    # https://bugs.debian.org/573496
    stdout = io.BytesIO()
    stderr = io.BytesIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(ocrodjvu.main, ['', '--version'])
    assert_equal(rc, 0)
    assert_not_equal(stderr.getvalue(), '')
    assert_equal(stdout.getvalue(), '')

def test_list_engines():
    global engines
    stdout = io.BytesIO()
    stderr = io.BytesIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(ocrodjvu.main, ['', '--list-engines'])
    assert_equal(rc, 0)
    assert_equal(stderr.getvalue(), '')
    engines = stdout.getvalue().splitlines()

def _test_list_languages(engine):
    stdout = io.BytesIO()
    stderr = io.BytesIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(ocrodjvu.main, ['', '--engine', engine, '--list-languages'])
    assert_equal(rc, 0)
    assert_equal(stderr.getvalue(), '')
    assert_not_equal(stdout.getvalue(), '')

def test_list_languages():
    assert_is_not_none(engines)
    for engine in engines:
        yield _test_list_languages, engine

# vim:ts=4 sts=4 sw=4 et
