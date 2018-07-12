# encoding=UTF-8

# Copyright © 2010-2016 Jakub Wilk <jwilk@jwilk.net>
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

import codecs
import contextlib
import glob
import locale
import logging
import os
import re
import sys

from nose import SkipTest

from nose.tools import (
    assert_equal,
    assert_false,
    assert_not_equal,
    assert_true,
)

import nose.tools

def noseimport(vmaj, vmin, name=None):
    def wrapper(f):
        if sys.version_info >= (vmaj, vmin):
            return getattr(nose.tools, name or f.__name__)
        return f
    return wrapper

@noseimport(2, 7)
def assert_greater_equal(x, y):
    assert_true(
        x >= y,
        msg='{0!r} not greater than or equal to {1!r}'.format(x, y)
    )

@noseimport(2, 7)
def assert_in(x, y):
    assert_true(
        x in y,
        msg='{0!r} not found in {1!r}'.format(x, y)
    )

@noseimport(2, 7)
def assert_is(x, y):
    assert_true(
        x is y,
        msg='{0!r} is not {1!r}'.format(x, y)
    )

@noseimport(2, 7)
def assert_is_instance(obj, cls):
    assert_true(
        isinstance(obj, cls),
        msg='{0!r} is not an instance of {1!r}'.format(obj, cls)
    )

@noseimport(2, 7)
def assert_is_none(obj):
    assert_is(obj, None)

@noseimport(2, 7)
def assert_is_not_none(obj):
    assert_true(
        obj is not None,
        msg='{0!r} is None'.format(obj)
    )

@noseimport(2, 7)
def assert_multi_line_equal(x, y):
    assert_equal(x, y)
if sys.version_info >= (2, 7):
    type(assert_multi_line_equal.__self__).maxDiff = None

@noseimport(2, 7)
class assert_raises(object):
    def __init__(self, exc_type):
        self._exc_type = exc_type
        self.exception = None
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            assert_true(False, '{0} not raised'.format(self._exc_type.__name__))
        if not issubclass(exc_type, self._exc_type):
            return False
        if isinstance(exc_value, exc_type):
            pass
            # This branch is not always taken in Python 2.6:
            # https://bugs.python.org/issue7853
        elif isinstance(exc_value, tuple):
            exc_value = exc_type(*exc_value)
        else:
            exc_value = exc_type(exc_value)
        self.exception = exc_value
        return True

@noseimport(2, 7, 'assert_raises_regexp')
@contextlib.contextmanager
def assert_raises_regex(exc_type, regex):
    with assert_raises(exc_type) as ecm:
        yield
    assert_regex(str(ecm.exception), regex)

@noseimport(2, 7, 'assert_regexp_matches')
def assert_regex(text, regex):
    if isinstance(regex, basestring):
        regex = re.compile(regex)
    if not regex.search(text):
        message = "Regex didn't match: {0!r} not found in {1!r}".format(regex.pattern, text)
        assert_true(False, msg=message)

@contextlib.contextmanager
def interim(obj, **override):
    copy = dict(
        (key, getattr(obj, key))
        for key in override
    )
    for key, value in override.iteritems():
        setattr(obj, key, value)
    try:
        yield
    finally:
        for key, value in copy.iteritems():
            setattr(obj, key, value)

@contextlib.contextmanager
def interim_environ(**override):
    keys = set(override)
    copy_keys = keys & set(os.environ)
    copy = dict(
        (key, value)
        for key, value in os.environ.iteritems()
        if key in copy_keys
    )
    for key, value in override.iteritems():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    try:
        yield
    finally:
        for key in keys:
            os.environ.pop(key, None)
        os.environ.update(copy)

def try_run(f, *args, **kwargs):
    '''Catch SystemExit etc.'''
    try:
        f(*args, **kwargs)
    except SystemExit as ex:
        return ex.code
    else:
        return 0

def sorted_glob(*args, **kwargs):
    return sorted(glob.iglob(*args, **kwargs))

def remove_logging_handlers(prefix):
    loggers = logging.Logger.manager.loggerDict.values()
    for logger in loggers:
        try:
            handlers = logger.handlers
        except AttributeError:
            continue
        for handler in handlers:
            if logger.name.startswith(prefix):
                logger.removeHandler(handler)

def require_locale_encoding(encoding):
    req_encoding = codecs.lookup(encoding).name
    locale_encoding = locale.getpreferredencoding()
    locale_encoding = codecs.lookup(locale_encoding).name
    if req_encoding != locale_encoding:
        raise SkipTest('locale encoding {enc} is required'.format(enc=encoding))

__all__ = [
    'assert_equal',
    'assert_false',
    'assert_greater_equal',
    'assert_in',
    'assert_is',
    'assert_is_instance',
    'assert_is_none',
    'assert_is_not_none',
    'assert_multi_line_equal',
    'assert_not_equal',
    'assert_raises',
    'assert_raises_regex',
    'assert_regex',
    'assert_true',
    'interim',
    'interim_environ',
    'remove_logging_handlers',
    'require_locale_encoding',
    'sorted_glob',
    'try_run',
]

# vim:ts=4 sts=4 sw=4 et
