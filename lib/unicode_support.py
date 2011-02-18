# encoding=UTF-8

# Copyright © 2008, 2009, 2010, 2011 Jakub Wilk <jwilk@jwilk.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

from . import utils

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
        utils.enhance_import_error(ex, 'PyICU', 'python-pyicu', 'http://pyicu.osafoundation.org/')
        raise

def simple_word_break_iterator(text):
    '''
    Create an instance of simple space-to-space word break interator.
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
    '''
    if locale is None:
        return simple_word_break_iterator(text)
    icu = get_icu()
    break_iterator = icu.BreakIterator.createWordInstance(locale)
    break_iterator.setText(text)
    return break_iterator

# vim:ts=4 sw=4 et
