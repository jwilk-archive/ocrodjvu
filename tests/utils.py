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

import sys
import warnings

from tests.common import *

import lib.utils
from lib.utils import *

class test_enhance_import():

    @classmethod
    def setup_class(cls):
        sys.modules['nonexistent'] = None

    def test_debian(self):
        with interim(lib.utils, debian=True):
            with raises(ImportError, 'No module named nonexistent; please install the python-nonexistent package'):
                try:
                    import nonexistent
                except ImportError, ex:
                    enhance_import_error(ex, 'PyNonexistent', 'python-nonexistent', 'http://pynonexistent.example.net/')
                    raise

    def test_nondebian(self):
        with interim(lib.utils, debian=False):
            with raises(ImportError, 'No module named nonexistent; please install the PyNonexistent package <http://pynonexistent.example.net/>'):
                try:
                    import nonexistent
                except ImportError, ex:
                    enhance_import_error(ex, 'PyNonexistent', 'python-nonexistent', 'http://pynonexistent.example.net/')
                    raise

class test_parse_page_numbers():

    def test_none(self):
        assert_true(parse_page_numbers(None) is None)

    def test_single(self):
        assert_equal(parse_page_numbers('17'), [17])

    def test_range(self):
        assert_equal(parse_page_numbers('37-42'), [37, 38, 39, 40, 41, 42])

    def test_multiple(self):
        assert_equal(parse_page_numbers('17,37-42'), [17, 37, 38, 39, 40, 41, 42])

    def test_bad_range(self):
        assert_equal(parse_page_numbers('42-37'), [])

    def test_collapsed_range(self):
        assert_equal(parse_page_numbers('17-17'), [17])

class test_sanitize_utf8():

    def test_control_characters(self):
        s = ''.join(map(chr, xrange(32)))
        t = sanitize_utf8(s).decode('UTF-8')
        assert_equal(t, u'\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\t\n\ufffd\ufffd\r\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd')

    def test_ascii(self):
        s = 'The quick brown fox jumps over the lazy dog'
        t = sanitize_utf8(s)
        assert_equal(s, t)

    def test_utf8(self):
        s = 'Jeżu klątw, spłódź Finom część gry hańb'
        t = sanitize_utf8(s)
        assert_equal(s, t)

class test_not_overriden():

    class B(object):
        @not_overridden
        def f(self, x, y):
            pass

    class C(B):
        def f(self, x, y):
            return x * y

    def test_not_overriden(self):
        with catch_warnings():
            warnings.filterwarnings('error', category=NotOverriddenWarning)
            with raises(NotOverriddenWarning, regex=r'^.*\bB.f[(][)] is not overridden$'):
                self.B().f(6, 7)

    def test_overriden(self):
        with catch_warnings():
            warnings.filterwarnings('error', category=NotOverriddenWarning)
            result = self.C().f(6, 7)
            assert_equal(result, 42)

def test_identity():
    o = object()
    assert_true(identity(o) is o)

# vim:ts=4 sw=4 et
