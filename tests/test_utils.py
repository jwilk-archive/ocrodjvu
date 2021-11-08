# encoding=UTF-8

# Copyright © 2010-2019 Jakub Wilk <jwilk@jwilk.net>
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
from builtins import map
from builtins import str
from builtins import range
from builtins import object
import sys
import warnings

from tests.tools import (
    assert_equal,
    assert_greater,
    assert_greater_equal,
    assert_in,
    assert_is,
    assert_is_instance,
    assert_is_none,
    assert_less_equal,
    assert_raises,
    assert_raises_regex,
    interim,
)

import lib.utils
from lib.utils import (
    EncodingWarning,
    NotOverriddenWarning,
    enhance_import_error,
    identity,
    not_overridden,
    parse_page_numbers,
    property,
    sanitize_utf8,
    smart_repr,
    str_as_unicode,
)

class test_enhance_import(object):

    @classmethod
    def setup_class(cls):
        sys.modules['nonexistent'] = None

    def test_debian(self):
        with interim(lib.utils, debian=True):
            with assert_raises(ImportError) as ecm:
                try:
                    import nonexistent
                except ImportError as ex:
                    enhance_import_error(ex, 'PyNonexistent', 'python-nonexistent', 'http://pynonexistent.example.net/')
                    raise
                nonexistent.f()  # quieten pyflakes
            assert_equal(str(ecm.exception),
                'import of nonexistent halted; None in sys.modules'
            )

    def test_nondebian(self):
        with interim(lib.utils, debian=False):
            with assert_raises(ImportError) as ecm:
                try:
                    import nonexistent
                except ImportError as ex:
                    enhance_import_error(ex, 'PyNonexistent', 'python-nonexistent', 'http://pynonexistent.example.net/')
                    raise
                nonexistent.f()  # quieten pyflakes
            assert_equal(str(ecm.exception),
                'import of nonexistent halted; None in sys.modules'
            )

    def test_no_debian_pkg(self):
        def t():
            with assert_raises(ImportError) as ecm:
                try:
                    import nonexistent
                except ImportError as ex:
                    enhance_import_error(ex, 'PyNonexistent', None, 'http://pynonexistent.example.net/')
                    raise
                nonexistent.f()  # quieten pyflakes
            assert_equal(str(ecm.exception),
                'import of nonexistent halted; None in sys.modules'
            )
        with interim(lib.utils, debian=False):
            t()
        with interim(lib.utils, debian=True):
            t()

# pylint: disable=eval-used
class test_smart_repr(object):

    def test_byte_string(self):
        print(smart_repr(''))
        for s in '', '\f', 'eggs', '''e'gg"s''', 'jeż', '''j'e"ż''':
            assert_equal(eval(smart_repr(s)), s)

    def test_unicode_string(self):
        for s in u'', u'\f', u'eggs', u'''e'gg"s''', u'jeż', u'''j'e"ż''':
            assert_equal(eval(smart_repr(s)), s)

    def test_encoded_string(self):
        for s in '', '\f', 'eggs', '''e'gg"s''':
            assert_equal(eval(smart_repr(s, 'ASCII')), s)
            assert_equal(eval(smart_repr(s, 'UTF-8')), s)
        for s in 'jeż', u'''j'e"ż''':
            s_repr = smart_repr(s, 'ASCII')
            assert_is_instance(s_repr, str)
            assert_equal(eval(s_repr), s)
        for s in u'jeż', u'''j'e"ż''':
            s_repr = smart_repr(s, 'UTF-8')
            assert_is_instance(s_repr, str)
            assert_in('ż', s_repr)
            assert_equal(eval(s_repr), s)
# pylint: enable=eval-used

class test_parse_page_numbers(object):

    def test_none(self):
        assert_is_none(parse_page_numbers(None))

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

class test_sanitize_utf8(object):

    def test_control_characters(self):
        def show(message, category, filename, lineno, file=None, line=None):
            with assert_raises_regex(EncodingWarning, '.*control character.*'):
                raise message
        s = (''.join(map(chr, range(32)))).encode('UTF-8')
        with warnings.catch_warnings():
            warnings.showwarning = show
            t = sanitize_utf8(s).decode('UTF-8')
        assert_equal(t,
            u'\uFFFD\uFFFD\uFFFD\uFFFD\uFFFD\uFFFD\uFFFD\uFFFD'
            u'\uFFFD\t\n\uFFFD\uFFFD\r\uFFFD\uFFFD'
            u'\uFFFD\uFFFD\uFFFD\uFFFD\uFFFD\uFFFD\uFFFD\uFFFD'
            u'\uFFFD\uFFFD\uFFFD\uFFFD\uFFFD\uFFFD\uFFFD\uFFFD'
        )

    def test_ascii(self):
        s = b'The quick brown fox jumps over the lazy dog'
        with warnings.catch_warnings():
            warnings.filterwarnings('error', category=EncodingWarning)
            t = sanitize_utf8(s)
        assert_equal(s, t)

    def test_utf8(self):
        s = 'Jeżu klątw, spłódź Finom część gry hańb'.encode('UTF-8')
        with warnings.catch_warnings():
            warnings.filterwarnings('error', category=EncodingWarning)
            t = sanitize_utf8(s)
        assert_equal(s, t)

    def test_non_utf8(self):
        def show(message, category, filename, lineno, file=None, line=None):
            with assert_raises_regex(EncodingWarning, '.* invalid continuation byte'):
                raise message
        s0 = 'Jeżu klątw, spłódź Finom część gry hańb'.encode('UTF-8')
        good = 'ó'
        bad = good.encode('ISO-8859-2')
        s1 = s0.replace(good.encode('UTF-8'), bad)
        s2 = s0.replace(good.encode('UTF-8'), u'\N{REPLACEMENT CHARACTER}'.encode('UTF-8'))
        with warnings.catch_warnings():
            warnings.showwarning = show
            t = sanitize_utf8(s1)
        assert_equal(s2, t)

class test_not_overridden(object):

    class B(object):
        @not_overridden
        def f(self, x, y):
            pass

    class C(B):
        def f(self, x, y):
            return x * y

    def test_not_overridden(self):
        def show(message, category, filename, lineno, file=None, line=None):
            with assert_raises_regex(NotOverriddenWarning, r'^.*\bB.f[(][)] is not overridden$'):
                raise message
        with warnings.catch_warnings():
            warnings.showwarning = show
            assert_is_none(self.B().f(6, 7))

    def test_overridden(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('error', category=NotOverriddenWarning)
            result = self.C().f(6, 7)
            assert_equal(result, 42)

class test_str_as_unicode(object):

    def test_ascii(self):
        for s in '', 'eggs', u'eggs':
            assert_equal(str_as_unicode(s), u'' + s)
            assert_equal(str_as_unicode(s, 'UTF-8'), u'' + s)
            assert_equal(str_as_unicode(s, 'ASCII'), u'' + s)

    def test_nonascii(self):
        rc = '\N{REPLACEMENT CHARACTER}'
        s = 'jeż'.encode('UTF-8')
        assert_equal(str_as_unicode(s, 'ASCII'), u'je' + rc + rc)
        assert_equal(str_as_unicode(s, 'UTF-8'), u'jeż')

    def test_unicode(self):
        s = u'jeż'
        assert_equal(str_as_unicode(s), s)
        assert_equal(str_as_unicode(s, 'ASCII'), s)
        assert_equal(str_as_unicode(s, 'UTF-8'), s)

def test_identity():
    o = object()
    assert_is(identity(o), o)

class test_property(object):

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
            assert_is_instance(obj, property)

    def test_default_filter(self):
        dummy = self.Dummy()
        assert_is_none(dummy.eggs)
        assert_equal(dummy.ham, 42)
        dummy.eggs = -4
        dummy.ham = -2
        assert_equal(dummy.eggs, -4)
        assert_equal(dummy.ham, -2)
        dummy = self.Dummy()
        assert_is_none(dummy.eggs)
        assert_equal(dummy.ham, 42)

def test_get_cpu_count():
    n = lib.utils.get_cpu_count()
    assert_is_instance(n, int)
    assert_greater_equal(n, 1)

def test_get_thread_limit():
    def t(nitems, njobs, xlim):
        lim = lib.utils.get_thread_limit(nitems, njobs)
        assert_equal(lim, xlim)
    for nitems in range(0, 10):
        for njobs in range(1, 10):
            lim = lib.utils.get_thread_limit(nitems, njobs)
            assert_is_instance(lim, int)
            if nitems == 0:
                assert_equal(lim, 1)
            else:
                npitems = min(nitems, njobs)
                assert_less_equal(lim * npitems, njobs)
                assert_greater((lim + 1) * npitems, njobs)

# vim:ts=4 sts=4 sw=4 et
