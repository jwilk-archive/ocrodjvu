# encoding=UTF-8

# Copyright © 2010 Jakub Wilk <jwilk@jwilk.net>
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

import os
import shlex
import shutil
import sys
from cStringIO import StringIO

from ocrodjvu.cli import djvu2hocr
from ocrodjvu import temporary
from ocrodjvu import ipc

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
        rc = try_run(djvu2hocr.main, ['', '--help'])
    assert_equal(rc, 0)
    assert_equal(stderr.getvalue(), '')
    assert_not_equal(stdout.getvalue(), '')

def test_version():
    # http://bugs.debian.org/573496
    stdout = StringIO()
    stderr = StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        rc = try_run(djvu2hocr.main, ['', '--version'])
    assert_equal(rc, 0)
    assert_not_equal(stderr.getvalue(), '')
    assert_equal(stdout.getvalue(), '')

def _test_from_file(base_filename, index):
    base_filename = os.path.join(here, base_filename)
    test_filename = '%s.test%d' % (base_filename, index)
    djvused_filename = base_filename + '.djvused'
    with open(test_filename, 'rb') as file:
        commandline = file.readline()
        expected_output = file.read()
    args = shlex.split(commandline)
    assert args[0] == '#'
    with temporary.directory() as tmpdir:
        djvu_filename = os.path.join(tmpdir, 'empty.djvu')
        args += [djvu_filename]
        shutil.copy(
            os.path.join(os.path.dirname(__file__), '..', 'common', 'empty.djvu'),
            djvu_filename)
        ipc.Subprocess(['djvused', '-f', djvused_filename, '-s', djvu_filename]).wait()
        xml_filename = os.path.join(tmpdir, 'output.html')
        with open(xml_filename, 'w+b') as xml_file:
            xmllint = ipc.Subprocess(['xmllint', '--format', '-'], stdin=ipc.PIPE, stdout=xml_file)
            try:
                with open(os.devnull, 'w') as null:
                    with interim(sys, stdout=xmllint.stdin, stderr=null):
                        with interim(djvu2hocr.logger, handlers=[]):
                            rc = try_run(djvu2hocr.main, args)
            finally:
                xmllint.stdin.close()
                try:
                    xmllint.wait()
                except ipc.CalledProcessError:
                    # Raising the exception here is likely to hide the real
                    # reason of the failure.
                    pass
            assert_equal(rc, 0)
            xml_file.seek(0)
            output = xml_file.read()
    assert_ml_equal(output, expected_output)

def test_from_file():
    for test_filename in sorted_glob(os.path.join(here, '*.test[0-9]')):
        index = int(test_filename[-1])
        base_filename = os.path.basename(test_filename[:-6])
        yield _test_from_file, base_filename, index

# vim:ts=4 sw=4 et
