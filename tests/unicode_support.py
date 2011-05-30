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

from tests.common import *

from lib.unicode_support import *

text = u'\u201cJekyll,\u201d cried Utterson, with a\xa0loud voice, \u201cI demand to see you.\u201d'

def test_simple_word_break_iterator():
    t = list(simple_word_break_iterator(text))
    s = [9, 10, 15, 16, 25, 26, 30, 31, 32, 33, 37, 38, 44, 45, 47, 48, 54, 55, 57, 58, 61, 62, 67]
    assert_equal(t, s)
    assert_equal(s[-1], len(text))

class test_word_break_iterator():

    def test_nolocale(self):
        t = list(word_break_iterator(text))
        s = [9, 10, 15, 16, 25, 26, 30, 31, 32, 33, 37, 38, 44, 45, 47, 48, 54, 55, 57, 58, 61, 62, 67]
        assert_equal(t, s)
        assert_equal(s[-1], len(text))

    def test_en(self):
        icu = get_icu()
        assert_not_equal(icu, None)
        t = list(word_break_iterator(text, icu.Locale('en')))
        s = [1, 7, 8, 9, 10, 15, 16, 24, 25, 26, 30, 31, 32, 33, 37, 38, 43, 44, 45, 46, 47, 48, 54, 55, 57, 58, 61, 62, 65, 66, 67]
        assert_equal(t, s)
        assert_equal(s[-1], len(text))

# vim:ts=4 sw=4 et
