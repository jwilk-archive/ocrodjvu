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

from __future__ import unicode_literals
from builtins import object
import os
import sys

from tests.tools import (
    assert_equal,
    assert_raises,
    assert_raises_regex,
    interim,
)

import lib.ipc
from lib.engines.cuneiform import (
    Engine,
)

here = os.path.dirname(__file__)
here = os.path.relpath(here)

class test_cuneiform(object):

    existing_languages = [
        ('eng', 'eng'),
        ('ger', 'deu'),
        ('ruseng', 'rus-eng'),
        ('ruseng', 'rus+eng'),
        ('ruseng', 'eng+rus'),
    ]
    missing_languages = 'tlh',

    fake_executable = 'fake-cuneiform'

    @classmethod
    def setup_class(cls):
        cls.engine = Engine(
            executable=os.path.join(here, cls.fake_executable)
        )

    def _test_has_language(self, lang, ok):
        if ok:
            self.engine.check_language(lang)
        else:
            with assert_raises_regex(lib.errors.MissingLanguagePack, '^language pack for the selected language (.+) is not available$'):
                self.engine.check_language(lang)

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
            assert_equal(args[0], self.engine.executable)
            assert_equal(args[1], '-l')
            assert_equal(args[2], lang1)
            raise EOFError
        with interim(lib.ipc, Subprocess=fake_subprocess):
            with assert_raises(EOFError):
                with self.engine.recognize(sys.stdin, lang1):
                    pass

    def test_recognize(self):
        for lang1, lang2 in self.existing_languages:
            yield self._test_recognize, lang1, lang2
            if lang1 != lang2:
                yield self._test_recognize, lang1, lang1

class test_cuneiform_multilang(test_cuneiform):

    existing_languages = test_cuneiform.existing_languages + [
        ('rus_cze', 'rus+ces'),
        ('rus_cze', 'ces+rus'),
    ]

    fake_executable = 'fake-cuneiform-multilang'

# vim:ts=4 sts=4 sw=4 et
