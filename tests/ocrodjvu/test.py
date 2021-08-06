# encoding=UTF-8

# Copyright © 2010-2020 Jakub Wilk <jwilk@jwilk.net>
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
import io
import os
import shutil
import sys

from lib import errors
from lib import temporary
from lib.cli import ocrodjvu

from tests.tools import (
    assert_equal,
    assert_is_not_none,
    assert_not_equal,
    interim,
    remove_logging_handlers,
    require_locale_encoding,
    try_run,
)

engines = None

def test_help():
    stdout = io.StringIO()
    stderr = io.StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(ocrodjvu.main, ['', '--help'])
    assert_equal(stderr.getvalue(), '')
    assert_equal(rc, 0)
    assert_not_equal(stdout.getvalue(), '')

def test_version():
    # https://bugs.debian.org/573496
    stdout = io.StringIO()
    stderr = io.StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(ocrodjvu.main, ['', '--version'])
    assert_equal(rc, 0)
    assert_equal(stderr.getvalue(), '')
    assert_not_equal(stdout.getvalue(), '')

def test_bad_options():
    stdout = io.StringIO()
    stderr = io.StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(ocrodjvu.main, [''])
    assert_equal(rc, errors.EXIT_FATAL)
    assert_not_equal(stderr.getvalue(), '')
    assert_equal(stdout.getvalue(), '')

def test_list_engines():
    global engines
    stdout = io.StringIO()
    stderr = io.StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(ocrodjvu.main, ['', '--list-engines'])
    assert_equal(stderr.getvalue(), '')
    assert_equal(rc, 0)
    engines = stdout.getvalue().splitlines()

def _test_list_languages(engine):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(ocrodjvu.main, ['', '--engine', engine, '--list-languages'])
    assert_equal(stderr.getvalue(), '')
    assert_equal(rc, 0)
    assert_not_equal(stdout.getvalue(), '')

def test_list_languages():
    assert_is_not_none(engines)
    for engine in engines:
        yield _test_list_languages, engine

def test_nonascii_path():
    require_locale_encoding('UTF-8')  # djvused breaks otherwise
    remove_logging_handlers('ocrodjvu.')
    here = os.path.dirname(__file__)
    here = os.path.abspath(here)
    path = os.path.join(here, '..', 'data', 'empty.djvu')
    stdout = io.StringIO()
    stderr = io.StringIO()
    with temporary.directory() as tmpdir:
        tmp_path = os.path.join(tmpdir, 'тмп.djvu')
        shutil.copy(path, tmp_path)
        with interim(sys, stdout=stdout, stderr=stderr):
            rc = try_run(ocrodjvu.main, ['', '--engine', '_dummy', '--in-place', tmp_path])
    assert_equal(stderr.getvalue(), '')
    assert_equal(rc, 0)
    assert_equal(stdout.getvalue(), '')

def test_bad_page_id():
    remove_logging_handlers('ocrodjvu.')
    here = os.path.dirname(__file__)
    here = os.path.abspath(here)
    path = os.path.join(here, '..', 'data', 'bad-page-id.djvu')
    stdout = io.StringIO()
    stderr = io.StringIO()
    with temporary.directory() as tmpdir:
        out_path = os.path.join(tmpdir, 'tmp.djvu')
        with interim(sys, stdout=stdout, stderr=stderr):
            with interim(ocrodjvu, system_encoding='ASCII'):
                rc = try_run(ocrodjvu.main, ['', '--engine', '_dummy', '--save-bundled', out_path, path])
    assert_equal(stderr.getvalue(), '')
    assert_equal(rc, 0)
    assert_equal(stdout.getvalue(), '')

# vim:ts=4 sts=4 sw=4 et
