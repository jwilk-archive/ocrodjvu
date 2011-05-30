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
            with exception(ImportError, 'No module named nonexistent; please install the python-nonexistent package'):
                try:
                    import nonexistent
                except ImportError, ex:
                    enhance_import_error(ex, 'PyNonexistent', 'python-nonexistent', 'http://pynonexistent.example.net/')
                    raise

    def test_nondebian(self):
        with interim(lib.utils, debian=False):
            with exception(ImportError, 'No module named nonexistent; please install the PyNonexistent package <http://pynonexistent.example.net/>'):
                try:
                    import nonexistent
                except ImportError, ex:
                    enhance_import_error(ex, 'PyNonexistent', 'python-nonexistent', 'http://pynonexistent.example.net/')
                    raise

class test_smart_repr():

    def test_byte_string(self):
        for s in '', '\f', 'eggs', '''e'gg"s''', 'jeż', '''j'e"ż''':
            assert_equal(eval(smart_repr(s)), s)

    def test_unicode_string(self):
        for s in u'', u'\f', u'eggs', u'''e'gg"s''', u'jeż', u'''j'e"ż''':
            assert_equal(eval(smart_repr(s)), s)

    def test_encoded_string(self):
        for s in '', '\f', 'eggs', '''e'gg"s''':
            assert_equal(eval(smart_repr(s, 'ASCII')), s)
            assert_equal(eval(smart_repr(s, 'UTF-8')), s)
        for s in 'jeż', '''j'e"ż''':
            s_repr = smart_repr(s, 'ASCII')
            assert_true(isinstance(s_repr, str))
            s_repr.decode('ASCII')
            assert_equal(eval(s_repr), s)
        for s in 'jeż', '''j'e"ż''':
            s_repr = smart_repr(s, 'UTF-8')
            assert_true(isinstance(s_repr, unicode))
            assert_true(u'ż' in s_repr)
            assert_equal(eval(s_repr.encode('UTF-8')), s)

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
        def show(message, category, filename, lineno, file=None, line=None):
            with exception(NotOverriddenWarning, regex=r'^.*\bB.f[(][)] is not overridden$'):
                raise message
        with catch_warnings():
            warnings.showwarning = show
            assert_true(self.B().f(6, 7) is None)

    def test_overriden(self):
        with catch_warnings():
            warnings.filterwarnings('error', category=NotOverriddenWarning)
            result = self.C().f(6, 7)
            assert_equal(result, 42)

class test_str_as_unicode():

    def test_ascii(self):
        for s in '', 'eggs', u'eggs':
            assert_equal(str_as_unicode(s), u'' + s)
            assert_equal(str_as_unicode(s, 'UTF-8'), u'' + s)
            assert_equal(str_as_unicode(s, 'ASCII'), u'' + s)

    def test_nonascii(self):
        rc = u'\N{REPLACEMENT CHARACTER}'
        s = 'jeż'
        assert_equal(str_as_unicode(s, 'ASCII'), 'je' + rc + rc)
        assert_equal(str_as_unicode(s, 'UTF-8'), u'jeż')

    def test_unicode(self):
        s = u'jeż'
        assert_equal(str_as_unicode(s), s)
        assert_equal(str_as_unicode(s, 'ASCII'), s)
        assert_equal(str_as_unicode(s, 'UTF-8'), s)

def test_identity():
    o = object()
    assert_true(identity(o) is o)

class test_property():

    @classmethod
    def setup_class(cls):
        class Dummy(object):
            eggs = property()
            ham = property(default_value=42)
        cls.Dummy = Dummy

    def test_class(self):
        eggs = self.Dummy.eggs
        ham = self.Dummy.ham
        for obj in eggs, ham:
            assert_true(isinstance(obj, property))

    def test_default_filter(self):
        dummy = self.Dummy()
        assert_equal(dummy.eggs, None)
        assert_equal(dummy.ham, 42)
        dummy.eggs = -4
        dummy.ham = -2
        assert_equal(dummy.eggs, -4)
        assert_equal(dummy.ham, -2)
        dummy = self.Dummy()
        assert_equal(dummy.eggs, None)
        assert_equal(dummy.ham, 42)

# vim:ts=4 sw=4 et
