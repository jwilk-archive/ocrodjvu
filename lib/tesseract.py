#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2009 Jakub Wilk <jwilk@jwilk.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

import glob
import os
import re

from . import errors
from . import ipc

_language_pattern = re.compile('^[a-z]{3}(-[a-z]+)?$')
_error_pattern = re.compile(r"^Unable to load unicharset file (/.*)/[.]unicharset\n$", re.DOTALL)

def get_tesseract_data_directory():
    try:
        tesseract = ipc.Subprocess(['tesseract', '', '', '-l', ''],
            stdout=ipc.PIPE,
            stderr=ipc.PIPE,
            env={}, # locale=POSIX
        )
    except OSError:
        raise errors.UnknownLanguageList
    try:
        line = tesseract.stderr.read()
        match = _error_pattern.match(line)
        if match is None:
            raise errors.UnknownLanguageList
        directory = match.group(1)
        if not os.path.isdir(directory):
            raise errors.UnknownLanguageList
    finally:
        try:
            tesseract.wait()
        except ipc.CalledProcessError, ex:
            pass
        else:
            raise errors.UnknownLanguageList
    return directory

def get_languages():
    directory = get_tesseract_data_directory()
    for filename in glob.glob(os.path.join(directory, '*.unicharset')):
        filename = os.path.basename(filename)
        language = os.path.splitext(filename)[0]
        if _language_pattern.match(language):
            yield language

def has_language(language):
    if not _language_pattern.match(language):
        raise errors.InvalidLanguageId(language)
    directory = get_tesseract_data_directory()
    return os.path.exists(os.path.join(directory, '%s.unicharset' % language))

# vim:ts=4 sw=4 et
