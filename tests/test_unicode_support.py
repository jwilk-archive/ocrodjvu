# encoding=UTF-8

# Copyright © 2010-2018 Jakub Wilk <jwilk@jwilk.net>
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

from tests.tools import (
    assert_equal,
    assert_not_equal,
)

from lib.unicode_support import (
    get_icu,
    simple_word_break_iterator,
    word_break_iterator,
)

text = u'\u201CJekyll,\u201D cried Utterson, with a\xa0loud voice, \u201CI demand to see you.\u201D'

class test_simple_word_break_iterator():

    def test_nonempty(self):
        t = list(simple_word_break_iterator(text))
        s = [9, 10, 15, 16, 25, 26, 30, 31, 32, 33, 37, 38, 44, 45, 47, 48, 54, 55, 57, 58, 61, 62, 67]
        assert_equal(t, s)
        assert_equal(s[-1], len(text))

    def test_empty(self):
        t = list(simple_word_break_iterator(''))
        assert_equal(t, [])

class test_word_break_iterator():

    def test_nolocale(self):
        t = list(word_break_iterator(text))
        s = [9, 10, 15, 16, 25, 26, 30, 31, 32, 33, 37, 38, 44, 45, 47, 48, 54, 55, 57, 58, 61, 62, 67]
        assert_equal(t, s)
        assert_equal(s[-1], len(text))

    def test_nolocale_empty(self):
        t = list(word_break_iterator(''))
        assert_equal(t, [])

    def test_en(self):
        icu = get_icu()
        assert_not_equal(icu, None)
        t = list(word_break_iterator(text, icu.Locale('en')))
        s = [1, 7, 8, 9, 10, 15, 16, 24, 25, 26, 30, 31, 32, 33, 37, 38, 43, 44, 45, 46, 47, 48, 54, 55, 57, 58, 61, 62, 65, 66, 67]
        assert_equal(t, s)
        assert_equal(s[-1], len(text))

    def test_en_empty(self):
        icu = get_icu()
        assert_not_equal(icu, None)
        t = list(word_break_iterator('', icu.Locale('en')))
        assert_equal(t, [])

# vim:ts=4 sts=4 sw=4 et
