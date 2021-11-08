# encoding=UTF-8

# Copyright © 2010-2021 Jakub Wilk <jwilk@jwilk.net>
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
import codecs
import contextlib
import glob
import locale
import logging
import os

from nose import SkipTest

from nose.tools import (
    assert_equal,
    assert_false,
    assert_greater,
    assert_greater_equal,
    assert_in,
    assert_is,
    assert_is_instance,
    assert_is_none,
    assert_is_not_none,
    assert_less,
    assert_less_equal,
    assert_multi_line_equal,
    assert_not_equal,
    assert_raises,
    assert_raises_regexp as assert_raises_regex,
    assert_regexp_matches as assert_regex,
    assert_true,
)

type(assert_multi_line_equal.__self__).maxDiff = None

@contextlib.contextmanager
def interim(obj, **override):
    copy = dict(
        (key, getattr(obj, key))
        for key in override
    )
    for key, value in override.items():
        setattr(obj, key, value)
    try:
        yield
    finally:
        for key, value in copy.items():
            setattr(obj, key, value)

@contextlib.contextmanager
def interim_environ(**override):
    keys = set(override)
    copy_keys = keys & set(os.environ)
    copy = dict(
        (key, value)
        for key, value in os.environ.items()
        if key in copy_keys
    )
    for key, value in override.items():
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
    loggers = list(logging.Logger.manager.loggerDict.values())
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
    'assert_greater',
    'assert_greater_equal',
    'assert_in',
    'assert_is',
    'assert_is_instance',
    'assert_is_none',
    'assert_is_not_none',
    'assert_less',
    'assert_less_equal',
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
