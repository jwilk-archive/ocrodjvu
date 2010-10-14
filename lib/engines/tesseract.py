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
import sys

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

def _wait_for_worker(worker):
    stderr = worker.stderr.readlines()
    try:
        worker.wait()
    except Exception:
        for line in stderr:
            sys.stderr.write(line)
        raise
    if len(stderr) == 1:
        [line] = stderr
        if line.startswith('Tesseract Open Source OCR Engine'):
            # Annoyingly, Tesseract prints its own name on standard error even
            # if nothing went wrong. Filter out such an unhelpful message.
            return
    for line in stderr:
        sys.stderr.write(line)

@contextlib.contextmanager
def recognize_plain_text(image_file, language, details=None):
    with temporary.directory() as output_dir:
        worker = ipc.Subprocess(
            ['tesseract', image_file.name, os.path.join(output_dir, 'tmp'), '-l', language],
            stderr=ipc.PIPE,
        )
        _wait_for_worker(worker)
        yield open(os.path.join(output_dir, 'tmp.txt'), 'rt')

@contextlib.contextmanager
def recognize_hocr(image_file, language, details=None):
    with temporary.directory() as output_dir:
        tessconf_path = os.path.join(output_dir, 'tessconf')
        with file(tessconf_path, 'wt') as tessconf:
            # Tesseract 3.00 doesn't come with any config file to enable hOCR
            # output. Let's create our own one.
            print >>tessconf, 'tessedit_create_hocr T'
        worker = ipc.Subprocess(
            ['tesseract', image_file.name, os.path.join(output_dir, 'tmp'), '-l', language, tessconf_path],
            stderr=ipc.PIPE,
        )
        _wait_for_worker(worker)
        yield open(os.path.join(output_dir, 'tmp.html'), 'r')

class ExtractSettings(object):

    def __init__(self, rotation=0, details=text_zones.TEXT_DETAILS_WORD, uax29=None, page_size=None, cuneiform=None):
        self.rotation = rotation
        self.page_size = page_size

class Engine(object):

    name = 'tesseract'
    image_format = image_io.TIFF

    def __init__(self):
        try:
            _, extension = get_tesseract_info()
        except errors.UnknownLanguageList:
            raise errors.EngineNotFound(self.name)
        if extension == 'traineddata':
            # Import hocr late, so that importing lxml is not triggered if hOCR
            # output is not used.
            from .. import hocr
            self._hocr = hocr
            self.output_format = 'html'
        else:
            self._hocr = None
            self.output_format = 'txt'

    get_default_language = staticmethod(get_default_language)
    has_language = staticmethod(has_language)
    list_languages = staticmethod(get_languages)

    def recognize(self, image_file, language, details=None):
        if self._hocr is None:
            f = recognize_plain_text
        else:
            f = recognize_hocr
        return f(image_file, language, details)

    def extract_text(self, stream, **kwargs):
        if self._hocr is not None:
            return self._hocr.extract_text(stream, **kwargs)
        settings = ExtractSettings(**kwargs)
        bbox = text_zones.BBox(*((0, 0) + settings.page_size))
        text = stream.read()
        zone = text_zones.Zone(const.TEXT_ZONE_PAGE, bbox, [text])
        zone.rotate(settings.rotation)
        return [zone.sexpr]

# vim:ts=4 sw=4 et
