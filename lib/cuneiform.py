#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2010 Jakub Wilk <ubanus@users.sf.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

import contextlib
import re
import tempfile

from . import errors
from . import ipc

_language_pattern = re.compile('^[a-z]{3}(-[a-z]+)?$')
_language_info_pattern = re.compile(r"^Supported languages: (.*)[.]$")

_cuneiform_to_iso = dict(
    ger='deu',
    ruseng='rus-eng', # mixed Russian-English
)

_iso_to_cuneiform = dict((y, x) for x, y in _cuneiform_to_iso.iteritems())

def cuneiform_to_iso(language):
    return _cuneiform_to_iso.get(language, language)

def iso_to_cuneiform(language):
    return _iso_to_cuneiform.get(language, language)

def get_languages():
    try:
        cuneiform = ipc.Subprocess(['cuneiform', '-l'],
            stdout=ipc.PIPE,
            stderr=ipc.PIPE,
            env=dict(LC_ALL='C', LANG='C')
        )
    except OSError:
        raise errors.UnknownLanguageList
    try:
        for line in cuneiform.stdout:
            m = _language_info_pattern.match(line)
            if m is None:
                continue
            return map(cuneiform_to_iso, m.group(1).split())
    finally:
        try:
            cuneiform.wait()
        except ipc.CalledProcessError, ex:
            pass
        else:
            raise error.UnknownLanguageList
    raise error.UnknownLanguageList

def has_language(language):
    if not _language_pattern.match(language):
        raise errors.InvalidLanguageId(language)
    return cuneiform_to_iso(language) in (language_list or get_languages())

def recognize(pbm_file, language):
    hocr_file = tempfile.NamedTemporaryFile(prefix='ocrodjvu.', suffix='.html')
    worker = ipc.Subprocess(
        ['cuneiform', '-l', language, '-f', 'hocr', '-o', hocr_file.name, pbm_file.name],
        stdout=ipc.PIPE,
    )
    worker.wait()
    return hocr_file

# vim:ts=4 sw=4 et
