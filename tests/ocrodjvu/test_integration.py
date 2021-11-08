# encoding=UTF-8

# Copyright © 2018 Jakub Wilk <jwilk@jwilk.net>
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
import distutils.spawn
import io
import os
import sys

from lib import temporary
from lib.cli import ocrodjvu

from tests.tools import (
    assert_multi_line_equal,
    assert_equal,
    interim,
    remove_logging_handlers,
    try_run,
    SkipTest,
)

engines = 'tesseract', 'cuneiform', 'gocr', 'ocrad'

def _test_ocr(engine, layers):
    if not distutils.spawn.find_executable(engine):
        raise SkipTest('{cmd} not found'.format(cmd=engine))
    remove_logging_handlers('ocrodjvu.')
    here = os.path.dirname(__file__)
    here = os.path.abspath(here)
    path = os.path.join(here, '..', 'data', 'alice.djvu')
    stdout = io.StringIO()
    stderr = io.StringIO()
    with temporary.directory() as tmpdir:
        tmp_path = os.path.join(tmpdir, 'tmp.djvu')
        with interim(sys, stdout=stdout, stderr=stderr):
            rc = try_run(ocrodjvu.main, ['', '--engine', engine, '--render', layers, '--save-bundled', tmp_path, path])
    assert_multi_line_equal(stderr.getvalue(), '')
    assert_equal(rc, 0)
    assert_multi_line_equal(stdout.getvalue(), '')

def test_ocr():
    for engine in engines:
        for layers in 'mask', 'all':
            yield _test_ocr, engine, layers

# vim:ts=4 sts=4 sw=4 et
