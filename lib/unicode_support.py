# encoding=UTF-8
# Copyright © 2008, 2009, 2010 Jakub Wilk <jwilk@jwilk.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

def get_icu():
    try:
        # For PyICU ≥ 1.0
        import icu
        return icu
    except ImportError:
        pass
    try:
        # For PyICU < 1.0
        import PyICU as icu
        return icu
    except ImportError, ex:
        ex.args = '%s; please install the PyICU package <http://pyicu.osafoundation.org/>' % str(ex),
        raise

def simple_word_break_iterator(text):
    '''
    Create an instance of simple space-to-space word break interator.
    >>> s = u'\u201cJekyll,\u201d cried Utterson, with a\xa0loud voice, \u201cI demand to see you.\u201d'
    >>> list(simple_word_break_iterator(s))
    [9, 10, 15, 16, 25, 26, 30, 31, 32, 33, 37, 38, 44, 45, 47, 48, 54, 55, 57, 58, 61, 62, 67]
    '''
    if not text:
        return
    space = text[0].isspace()
    for n, ch in enumerate(text):
        if space != ch.isspace():
            yield n
            space = not space
    yield len(text)

def word_break_iterator(text, locale=None):
    '''
    Create an instance of word break interator.

    text: unicode string
    locale: ICU locale or None

    >>> icu = get_icu()
    >>> s = u'\u201cJekyll,\u201d cried Utterson, with a\xa0loud voice, \u201cI demand to see you.\u201d'
    >>> list(word_break_iterator(s))
    [9, 10, 15, 16, 25, 26, 30, 31, 32, 33, 37, 38, 44, 45, 47, 48, 54, 55, 57, 58, 61, 62, 67]
    >>> list(word_break_iterator(s, icu.Locale('en')))
    [1, 7, 8, 9, 10, 15, 16, 24, 25, 26, 30, 31, 32, 33, 37, 38, 43, 44, 45, 46, 47, 48, 54, 55, 57, 58, 61, 62, 65, 66, 67]
    '''
    if locale is None:
        return simple_word_break_iterator(text)
    icu = get_icu()
    break_iterator = icu.BreakIterator.createWordInstance(locale)
    break_iterator.setText(text)
    return break_iterator

# vim:ts=4 sw=4 et
