# encoding=UTF-8

# Copyright © 2010-2015 Jakub Wilk <jwilk@jwilk.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

import contextlib
import glob
import os
import re
import sys
import warnings

from nose.tools import (
    assert_equal,
    assert_false,
    assert_not_equal,
    assert_true,
)

if sys.version_info >= (2, 7):
    from nose.tools import (
        assert_greater_equal,
        assert_in,
        assert_is,
        assert_is_instance,
        assert_is_none,
        assert_is_not_none,
        assert_multi_line_equal,
        assert_raises,
        assert_raises_regexp,
        assert_regexp_matches,
    )
    assert_multi_line_equal.im_class.maxDiff = None
else:
    # Python 2.6:
    def assert_greater_equal(x, y):
        assert_true(
            x >= y,
            msg='{0!r} not greater than or equal to {1!r}'.format(x, y)
        )
    def assert_in(x, y):
        assert_true(
            x in y,
            msg='{0!r} not found in {1!r}'.format(x, y)
        )
    def assert_is(x, y):
        assert_true(
            x is y,
            msg='{0!r} is not {1!r}'.format(x, y)
        )
    def assert_is_instance(obj, cls):
        assert_true(
            isinstance(obj, cls),
            msg='{0!r} is not an instance of {1!r}'.format(obj, cls)
        )
    def assert_is_none(obj):
        assert_is(obj, None)
    def assert_is_not_none(obj):
        assert_true(
            obj is not None,
            msg='{0!r} is None'.format(obj)
        )
    assert_multi_line_equal = assert_equal
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
    @contextlib.contextmanager
    def assert_raises_regexp(exc_type, regexp):
        with assert_raises(exc_type) as ecm:
            yield
        assert_regexp_matches(str(ecm.exception), regexp)
    def assert_regexp_matches(text, regexp):
        if isinstance(regexp, basestring):
            regexp = re.compile(regexp)
        if not regexp.search(text):
            message = "Regexp didn't match: {0!r} not found in {1!r}".format(regexp.pattern, text)
            assert_true(False, msg=message)

@contextlib.contextmanager
def interim(obj, **override):
    copy = dict((key, getattr(obj, key)) for key in override)
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
    copy = dict((key, value) for key, value in os.environ.iteritems() if key in copy_keys)
    for key, value in override.iteritems():
        if value is None:
            try:
                del os.environ[key]
            except KeyError:
                pass
        else:
            os.environ[key] = value
    try:
        yield
    finally:
        for key in keys:
            try:
                del os.environ[key]
            except KeyError:
                pass
        os.environ.update(copy)

def try_run(f, *args, **kwargs):
    '''Catch SystemExit etc.'''
    try:
        f(*args, **kwargs)
    except SystemExit as ex:
        return ex.code
    else:
        return 0

try:
    catch_warnings = warnings.catch_warnings
except AttributeError:
    @contextlib.contextmanager
    def catch_warnings():
        original_filters = warnings.filters
        original_show = warnings.showwarning
        try:
            yield
        finally:
            warnings.filters = original_filters
            warnings.showwarning = original_show

@contextlib.contextmanager
def exception(exc_type, string=None, regex=None, callback=None):
    if sum(x is not None for x in (string, regex, callback)) != 1:
        raise ValueError('exactly one of: string, regex, callback must be provided')
    if string is not None:
        def callback(exc):
            assert_equal(str(exc), string)
    elif regex is not None:
        def callback(exc):
            exc_string = str(exc)
            if not re.match(regex, exc_string):
                message = "regexp didn't match: {re!r} not found in {exc!r}".format(re=regex, exc=exc_string)
                raise AssertionError(message)
    try:
        yield None
    except exc_type:
        _, exc, _ = sys.exc_info()
        callback(exc)
    else:
        message = '{exc} was not raised'.format(exc=exc_type.__name__)
        raise AssertionError(message)

def sorted_glob(*args, **kwargs):
    return sorted(glob.iglob(*args, **kwargs))

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
    'assert_true',
    'assert_raises',
    'assert_raises_regexp',
    'assert_regexp_matches',
    'catch_warnings',
    'interim',
    'interim_environ',
    'sorted_glob',
    'try_run',
]

# vim:ts=4 sts=4 sw=4 et
