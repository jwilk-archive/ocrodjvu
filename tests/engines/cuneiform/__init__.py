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

from __future__ import with_statement

import os
import sys

from tests.common import (
    assert_equal,
    exception,
    interim,
)

import lib.ipc
from lib.engines.cuneiform import (
    Engine,
)

here = os.path.dirname(__file__)
try:
    here = os.path.relpath(here)
except AttributeError:
    # Python 2.5. No big deal.
    pass

engine = None

def setup_module():
    global engine
    engine = Engine(executable=os.path.join(here, 'fake-executable'))

class test_language():

    existing_languages = (
        ('eng', 'eng'),
        ('ger', 'deu'),
        ('ruseng', 'rus-eng'),
        ('ruseng', 'rus+eng'),
        ('ruseng', 'eng+rus'),
    )
    missing_languages = 'tlh',

    def _test_has_language(self, lang, ok):
        if ok:
            engine.check_language(lang)
        else:
            with exception(lib.errors.MissingLanguagePack, regex='^language pack for the selected language (.+) is not available$'):
                engine.check_language(lang)

    def test_has_language(self):
        for lang1, lang2 in self.existing_languages:
            yield self._test_has_language, lang1, True
            if lang1 != lang2:
                yield self._test_has_language, lang2, True
        for lang in self.missing_languages:
            yield self._test_has_language, lang, False

    def _test_recognize(self, lang1, lang2):
        def fake_subprocess(args, *rest, **kwrest):
            # Record arguments that were used and break immediately.
            assert_equal(args[0], engine.executable)
            assert_equal(args[1], '-l')
            assert_equal(args[2], lang1)
            raise EOFError
        with interim(lib.ipc, Subprocess=fake_subprocess):
            with exception(EOFError, ''):
                with engine.recognize(sys.stdin, lang1):
                    pass

    def test_recognize(self):
        for lang1, lang2 in self.existing_languages:
            yield self._test_recognize, lang1, lang2
            if lang1 != lang2:
                yield self._test_recognize, lang1, lang1

# vim:ts=4 sts=4 sw=4 et
