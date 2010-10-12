# encoding=UTF-8
# Copyright © 2009, 2010 Jakub Wilk <jwilk@jwilk.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

from __future__ import with_statement

import contextlib
import glob
import os
import re
import shutil

from .. import errors
from .. import image_io
from .. import ipc
from .. import temporary
from .. import text_zones

const = text_zones.const

_language_pattern = re.compile('^[a-z]{3}(-[a-z]+)?$')
_error_pattern = re.compile(r"^(Error openn?ing data|Unable to load unicharset) file (?P<dir>/.*)/[.](?P<ext>[a-z]+)\n$", re.DOTALL)

def get_tesseract_info():
    try:
        tesseract = ipc.Subprocess(['tesseract', '', '', '-l', ''],
            stdout=ipc.PIPE,
            stderr=ipc.PIPE,
        )
    except OSError:
        raise errors.UnknownLanguageList
    try:
        line = tesseract.stderr.read()
        match = _error_pattern.match(line)
        if match is None:
            raise errors.UnknownLanguageList
        directory = match.group('dir')
        extension = match.group('ext')
        if not os.path.isdir(directory):
            raise errors.UnknownLanguageList
    finally:
        try:
            tesseract.wait()
        except ipc.CalledProcessError:
            pass
        else:
            raise errors.UnknownLanguageList
    return directory, extension

def get_languages():
    directory, extension = get_tesseract_info()
    for filename in glob.glob(os.path.join(directory, '*.%s' % extension)):
        filename = os.path.basename(filename)
        language = os.path.splitext(filename)[0]
        if _language_pattern.match(language):
            yield language

def has_language(language):
    if not _language_pattern.match(language):
        raise errors.InvalidLanguageId(language)
    directory, extension = get_tesseract_info()
    return os.path.exists(os.path.join(directory, '%s.%s' % (language, extension)))

def get_default_language():
    return os.getenv('tesslanguage') or 'eng'

@contextlib.contextmanager
def recognize(image_file, language, details=None):
    with temporary.directory() as output_dir:
        worker = ipc.Subprocess(
            ['tesseract', image_file.name, os.path.join(output_dir, 'tmp'), '-l', language],
            stderr=ipc.PIPE,
        )
        worker.wait()
        yield open(os.path.join(output_dir, 'tmp.txt'), 'rt')

class ExtractSettings(object):

    def __init__(self, rotation=0, details=text_zones.TEXT_DETAILS_WORD, uax29=None, page_size=None, cuneiform=None):
        self.rotation = rotation
        self.page_size = page_size

class Engine(object):

    name = 'tesseract'
    image_format = image_io.TIFF
    output_format = 'txt'

    def __init__(self):
        try:
            list(get_languages())
        except errors.UnknownLanguageList:
            raise errors.EngineNotFound(self.name)

    get_default_language = staticmethod(get_default_language)
    has_language = staticmethod(has_language)
    list_languages = staticmethod(get_languages)
    recognize = staticmethod(recognize)

    @staticmethod
    def extract_text(stream, **kwargs):
        settings = ExtractSettings(**kwargs)
        bbox = text_zones.BBox(*((0, 0) + settings.page_size))
        text = stream.read()
        zone = text_zones.Zone(const.TEXT_ZONE_PAGE, bbox, [text])
        zone.rotate(settings.rotation)
        return [zone.sexpr]

# vim:ts=4 sw=4 et
