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

def test_help():
    stdout = StringIO()
    stderr = StringIO()
    with interim(sys, stdout=stdout, stderr=stderr):
        try:
            ocrodjvu.main(['', '--help'])
        except SystemExit, ex:
            rc = ex.code
        else:
            rc = 0
    assert_equal(rc, 0)
    assert_equal(stderr.getvalue(), '')
    assert_not_equal(stdout.getvalue(), '')

# vim:ts=4 sw=4 et
