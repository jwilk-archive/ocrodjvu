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

import re

def parse_page_numbers(pages):
    '''
    >>> parse_page_numbers(None)

    >>> parse_page_numbers('17')
    [17]

    >>> parse_page_numbers('37-42')
    [37, 38, 39, 40, 41, 42]

    >>> parse_page_numbers('17,37-42')
    [17, 37, 38, 39, 40, 41, 42]

    >>> parse_page_numbers('42-37')
    []

    >>> parse_page_numbers('17-17')
    [17]
    '''
    if pages is None:
        return
    result = []
    for page_range in pages.split(','):
        if '-' in page_range:
            x, y = map(int, page_range.split('-', 1))
            result += xrange(x, y + 1)
        else:
            result += int(page_range, 10),
    return result

_special_chars_replace = re.compile(ur'''[\x00-\x1f'"\x5c\x7f-\x9f]''', re.UNICODE).sub

def _special_chars_escape(m):
    ch = m.group(0)
    if ch in ('"', "'"):
        return '\\' + ch
    else:
        return repr(ch)[2:-1]

def smart_repr(s, encoding=None):
    if encoding is None:
        return repr(s)
    try:
        u = s.decode(encoding)
    except UnicodeDecodeError:
        return repr(s)
    return "'%s'" % _special_chars_replace(_special_chars_escape, u)

def sanitize_utf8(text):
    r'''
    Replace invalid UTF-8 sequences and control characters (except CR, LF, TAB
    and space) with Unicode replacement characters.

    >>> s = ''.join(map(chr, xrange(32)))
    >>> sanitize_utf8(s).decode('UTF-8')
    u'\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\t\n\ufffd\ufffd\r\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd'

    >>> s = 'The quick brown fox jumps over the lazy dog'
    >>> sanitize_utf8(s) == s
    True

    >>> s = 'Je\xc5\xbcu kl\xc4\x85tw, sp\xc5\x82\xc3\xb3d\xc5\xba Finom cz\xc4\x99\xc5\x9b\xc4\x87 gry ha\xc5\x84b!'
    >>> sanitize_utf8(s) == s
    True
    '''
    text = text.decode('UTF-8', 'replace')
    for ch in map(unichr, xrange(32)):
        if ch in u'\n\r\t':
            continue
        text = text.replace(ch, u'\N{REPLACEMENT CHARACTER}')
    return text.encode('UTF-8')

# vim:ts=4 sw=4 et
