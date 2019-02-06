# encoding=UTF-8

# Copyright © 2010-2019 Jakub Wilk <jwilk@jwilk.net>
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

import os
import re
import shlex
import warnings

from . import common
from .. import errors
from .. import image_io
from .. import ipc
from .. import iso639
from .. import temporary
from .. import utils

_language_pattern = re.compile('^[a-z]{3}(?:[+][a-z]{3})*$')
_language_info_pattern = re.compile(r"^Supported languages: (.*)[.]$")

class Engine(common.Engine):

    name = 'cuneiform'
    image_format = image_io.BMP
    needs_utf8_fix = True

    executable = utils.property('cuneiform')
    extra_args = utils.property([], shlex.split)
    fix_html = utils.property(0, int)
    # fix_html currently does nothing, but we left it, as it might become
    # useful again at some point in the future.

    def __init__(self, *args, **kwargs):
        common.Engine.__init__(self, *args, **kwargs)
        self._user_to_cuneiform = None  # to be defined later
        self._cuneiform_to_iso = None  # to be defined later
        try:
            self._languages = list(self._get_languages())
        except errors.UnknownLanguageList:
            raise errors.EngineNotFound(self.name)
        # Import hocr late,
        # so that lxml is imported only when needed.
        from .. import hocr
        self._hocr = hocr

    def _get_languages(self):
        try:
            cuneiform = ipc.Subprocess([self.executable, '-l'],
                stdout=ipc.PIPE,
                stderr=ipc.PIPE,
            )
        except OSError:
            raise errors.UnknownLanguageList
        self._cuneiform_to_iso = {}
        self._user_to_cuneiform = {}
        try:
            for line in cuneiform.stdout:
                m = _language_info_pattern.match(line)
                if m is None:
                    continue
                codes = m.group(1).split()
                for code in codes:
                    if code == 'ruseng':
                        isocode = 'rus+eng'
                        # For compatibility with ocrodjvu ≤ 0.7.14:
                        self._user_to_cuneiform[frozenset(['rus-eng'])] = code
                    elif code == 'slo':
                        if 'slv' not in codes:
                            # Cuneiform ≤ 1.0 mistakenly uses ‘slo’ as language code
                            # for Slovenian.
                            # https://bugs.launchpad.net/cuneiform-linux/+bug/707951
                            isocode = 'slv'
                        else:
                            # Both ‘slo’ and ‘slv’ are available. Let's guess that
                            # the former means Slovak.
                            isocode = 'slk'
                    else:
                        try:
                            isocode = '+'.join(
                                iso639.b_to_t(c) for c in code.split('_')
                            )
                        except ValueError:
                            warnings.warn(
                                'unparsable language code: {0!r}'.format(code),
                                category=RuntimeWarning,
                                stacklevel=2
                            )
                    self._cuneiform_to_iso[code] = isocode
                    self._user_to_cuneiform[frozenset(isocode.split('+'))] = code
                    yield isocode
                return
        finally:
            try:
                cuneiform.wait()
            except ipc.CalledProcessError:
                pass
            else:
                raise errors.UnknownLanguageList
        raise errors.UnknownLanguageList

    def check_language(self, language):
        if language == 'slo':
            # Normally we accept Cuneiform-specific language code. This is an
            # exception: ‘slo’ is Slovenian in Cuneiform ≤ 1.0 but it is Slovak
            # according to ISO 639-2.
            language = 'slk'
        else:
            language = self.cuneiform_to_iso(language)
        language = self.normalize_iso(language)
        if not _language_pattern.match(language):
            raise errors.InvalidLanguageId(language)
        if language not in self._languages:
            raise errors.MissingLanguagePack(language)

    def list_languages(self):
        return iter(self._languages)

    def user_to_cuneiform(self, language):
        language_set = frozenset(
            iso639.b_to_t(code, permissive=True)
            for code in language.split('+')
        )
        return self._user_to_cuneiform.get(language_set, language)

    def cuneiform_to_iso(self, language):
        return self._cuneiform_to_iso.get(language, language)

    def normalize_iso(self, language):
        language = self.user_to_cuneiform(language)
        language = self.cuneiform_to_iso(language)
        return language

    def recognize(self, image, language, *args, **kwargs):
        with temporary.directory() as hocr_directory:
            # A separate non-world-writable directory is needed, as Cuneiform
            # can create additional files, e.g. images.
            hocr_file_name = os.path.join(hocr_directory, 'ocr.html')
            worker = ipc.Subprocess(
                [
                    self.executable,
                    '-l', self.user_to_cuneiform(language),
                    '-f', 'hocr',
                    '-o', hocr_file_name
                ] + self.extra_args + [image.name],
                stdin=ipc.PIPE,
                stdout=ipc.PIPE,
            )
            worker.stdin.close()
            worker.wait()
            with open(hocr_file_name, 'r') as hocr_file:
                return common.Output(
                    hocr_file.read(),
                    format='html',
                )

    def extract_text(self, *args, **kwargs):
        return self._hocr.extract_text(*args, **kwargs)

# vim:ts=4 sts=4 sw=4 et
