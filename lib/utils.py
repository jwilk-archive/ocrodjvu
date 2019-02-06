# encoding=UTF-8

# Copyright © 2008-2019 Jakub Wilk <jwilk@jwilk.net>
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

import functools
import locale
import os
import re
import warnings

debian = os.path.exists('/etc/debian_version')

def enhance_import_error(exception, package, debian_package, homepage):
    message = str(exception)
    if not debian:
        debian_package = None
    if debian_package is not None:
        package = debian_package
    message += '; please install the {pkg} package'.format(pkg=package)
    if debian_package is None:
        message += ' <{url}>'.format(url=homepage)
    exception.args = [message]

def parse_page_numbers(pages):
    '''
    parse_page_numbers(None) -> None
    parse_page_numbers('17') -> [17]
    parse_page_numbers('37-42') -> [37, 38, ..., 42]
    parse_page_numbers('17,37-42') -> [17, 37, 38, ..., 42]
    parse_page_numbers('42-37') -> []
    parse_page_numbers('17-17') -> [17]
    '''
    if pages is None:
        return
    result = []
    for page_range in pages.split(','):
        if '-' in page_range:
            x, y = map(int, page_range.split('-', 1))
            result += xrange(x, y + 1)
        else:
            result += [int(page_range, 10)]
    return result

_special_chars_replace = re.compile(ur'''[\x00-\x1F'"\x5C\x7F-\x9F]''').sub

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
    u = _special_chars_replace(_special_chars_escape, u)
    s = u.encode(encoding)
    return "'{0}'".format(s)

class EncodingWarning(UserWarning):
    pass

_control_characters_regex = re.compile('[{0}]'.format(''.join(
    ch for ch in map(chr, xrange(32))
    if ch not in u'\n\r\t'
)))

def sanitize_utf8(text):
    '''
    Replace invalid UTF-8 sequences and control characters (except CR, LF, TAB
    and space) with Unicode replacement characters.
    '''
    try:
        text = text.decode('UTF-8')
    except UnicodeDecodeError as exc:
        text = text.decode('UTF-8', 'replace')
        message = str(exc)
        message = re.sub("^'utf8' codec can't decode ", '', message)
        warnings.warn(
            message,
            category=EncodingWarning,
            stacklevel=2,
        )
    text = text.encode('UTF-8')
    match = _control_characters_regex.search(text)
    if match:
        byte = ord(match.group())
        message = 'byte 0x{byte:02x} in position {i}: control character'.format(byte=byte, i=match.start())
        warnings.warn(
            message,
            category=EncodingWarning,
            stacklevel=2,
        )
        text = _control_characters_regex.sub(u'\N{REPLACEMENT CHARACTER}'.encode('UTF-8'), text)
    # There are other code points that are not allowed in XML (or even: not
    # allowed in UTF-8), but which Python happily accept. However, they haven't
    # seemed to occur in real-world documents.
    # http://www.w3.org/TR/2008/REC-xml-20081126/#NT-Char
    return text

class NotOverriddenWarning(UserWarning):
    pass

def not_overridden(f):
    '''
    Issue NotOverriddenWarning if the decorated method was not overridden in a
    subclass, or called directly.
    '''
    @functools.wraps(f)
    def new_f(self, *args, **kwargs):
        cls = type(self)
        warnings.warn(
            '{mod}.{cls}.{func}() is not overridden'.format(mod=cls.__module__, cls=cls.__name__, func=f.__name__),
            category=NotOverriddenWarning,
            stacklevel=2
        )
        return f(self, *args, **kwargs)
    return new_f

def str_as_unicode(s, encoding=locale.getpreferredencoding()):
    if isinstance(s, unicode):
        return s
    return s.decode(encoding, 'replace')

def identity(x):
    '''
    identity(x) -> x
    '''
    return x

class property(object):

    def __init__(self, default_value=None, filter=identity):
        self._private_name = '__{mod}__{id}'.format(mod=self.__module__, id=id(self))
        self._filter = filter
        self._default_value = default_value

    def __get__(self, instance, cls):
        if instance is None:
            return self
        return getattr(instance, self._private_name, self._default_value)

    def __set__(self, instance, value):
        setattr(instance, self._private_name, self._filter(value))
        return

def get_cpu_count():
    try:
        import multiprocessing
        return multiprocessing.cpu_count()
    except (ImportError, NotImplementedError):  # no coverage
        pass
    try:  # no coverage
        return os.sysconf('SC_NPROCESSORS_ONLN')
    except (ValueError, OSError, AttributeError):  # no coverage
        return 1

def get_thread_limit(nitems, njobs):
    if nitems == 0:
        return 1
    return max(1, njobs // nitems)

# vim:ts=4 sts=4 sw=4 et
