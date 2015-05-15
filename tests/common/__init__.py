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
import difflib
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

def assert_ml_equal(first, second, msg='Strings differ'):
    '''Assert that two multi-line strings are equal.'''
    assert_true(isinstance(first, basestring), 'First argument is not a string')
    assert_true(isinstance(second, basestring), 'Second argument is not a string')
    if first == second:
        return
    first = first.splitlines(True)
    second = second.splitlines(True)
    diff = '\n' + ''.join(difflib.unified_diff(first, second))
    raise AssertionError(msg + diff)

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
    except SystemExit, ex:
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
                message = '%r !~ %r' % (exc_string, regex)
                raise AssertionError(message)
    try:
        yield None
    except exc_type:
        _, exc, _ = sys.exc_info()
        callback(exc)
    else:
        message = '%s was not raised' % exc_type.__name__
        raise AssertionError(message)

def sorted_glob(*args, **kwargs):
    return sorted(glob.iglob(*args, **kwargs))

__all__ = [
    'assert_equal',
    'assert_false',
    'assert_ml_equal',
    'assert_not_equal',
    'assert_true',
    'catch_warnings',
    'exception',
    'interim',
    'interim_environ',
    'sorted_glob',
    'try_run',
]

# vim:ts=4 sts=4 sw=4 et
