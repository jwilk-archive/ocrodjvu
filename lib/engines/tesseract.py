# encoding=UTF-8

# Copyright © 2009, 2010, 2011 Jakub Wilk <jwilk@jwilk.net>
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

import cgi
import contextlib
import glob
import os
import re
import shlex
import sys
from cStringIO import StringIO

from . import common
from .. import errors
from .. import image_io
from .. import ipc
from .. import temporary
from .. import text_zones
from .. import utils

const = text_zones.const

_language_pattern = re.compile('^[a-z]{3}(-[a-z]+)?$')
_error_pattern = re.compile(r"^(Error openn?ing data|Unable to load unicharset) file (?P<dir>/.*)/[.](?P<ext>[a-z]+)\n")

_bbox_extras_template = '''\
<!-- The following script was appended to hOCR by ocrodjvu -->
<script type='ocrodjvu/tesseract'>%s</script>
'''

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

def fix_html(s):
    '''
    Work around buggy hOCR output:
    http://code.google.com/p/tesseract-ocr/issues/detail?id=376
    '''
    regex = re.compile(
        r'''
        ( <[!/]?[a-z]+(?:\s+[^<>]*)?>
        | &[a-z]+;
        | &[#][0-9]+;
        | &[#]x[0-9a-f]+;
        | [^<>&]+
        )
        ''', re.IGNORECASE | re.VERBOSE
    )
    return ''.join(
        chunk if n & 1 else cgi.escape(chunk)
        for n, chunk in enumerate(regex.split(s))
    )

class ExtractSettings(object):

    def __init__(self, rotation=0, details=text_zones.TEXT_DETAILS_WORD, uax29=None, page_size=None, cuneiform=None):
        self.rotation = rotation
        self.page_size = page_size

class Engine(common.Engine):

    name = 'tesseract'
    image_format = image_io.TIFF

    executable = utils.property('tesseract')
    extra_args = utils.property([], shlex.split)
    use_hocr = utils.property(None, int)
    fix_html = utils.property(0, int)

    def __init__(self, *args, **kwargs):
        assert args == ()
        common.Engine.__init__(self, **kwargs)
        try:
            self._directory, self._extension = self.get_filesystem_info()
        except errors.UnknownLanguageList:
            raise errors.EngineNotFound(self.name)
        if self.use_hocr is None:
            self.use_hocr = self._extension == 'traineddata'
        if self.use_hocr:
            # Import hocr late, so that importing lxml is not triggered if hOCR
            # output is not used.
            from .. import hocr
            self._hocr = hocr
            self.output_format = 'html'
        else:
            self._hocr = None
            self.output_format = 'txt'

    def get_filesystem_info(self):
        try:
            tesseract = ipc.Subprocess([self.executable, '', '', '-l', ''],
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

    def list_languages(self):
        for filename in glob.glob(os.path.join(self._directory, '*.%s' % self._extension)):
            filename = os.path.basename(filename)
            language = os.path.splitext(filename)[0]
            if _language_pattern.match(language):
                yield language

    def has_language(self, language):
        if not _language_pattern.match(language):
            raise errors.InvalidLanguageId(language)
        return os.path.exists(os.path.join(self._directory, '%s.%s' % (language, self._extension)))

    @classmethod
    def get_default_language(cls):
        return os.getenv('tesslanguage') or 'eng'

    @contextlib.contextmanager
    def recognize_plain_text(self, image, language, details=None, uax29=None):
        with temporary.directory() as output_dir:
            worker = ipc.Subprocess(
                [self.executable, image.name, os.path.join(output_dir, 'tmp'), '-l', language] + self.extra_args,
                stderr=ipc.PIPE,
            )
            _wait_for_worker(worker)
            with open(os.path.join(output_dir, 'tmp.txt'), 'rt') as file:
                yield file

    @contextlib.contextmanager
    def recognize_hocr(self, image, language, details=text_zones.TEXT_DETAILS_WORD, uax29=None):
        character_details = details < text_zones.TEXT_DETAILS_WORD or (uax29 and details <= text_zones.TEXT_DETAILS_WORD)
        with temporary.directory() as output_dir:
            tessconf_path = os.path.join(output_dir, 'tessconf')
            with open(tessconf_path, 'wt') as tessconf:
                # Tesseract 3.00 doesn't come with any config file to enable hOCR
                # output. Let's create our own one.
                print >>tessconf, 'tessedit_create_hocr T'
            worker = ipc.Subprocess(
                [self.executable, image.name, os.path.join(output_dir, 'tmp'), '-l', language, tessconf_path] + self.extra_args,
                stderr=ipc.PIPE,
            )
            _wait_for_worker(worker)
            with open(os.path.join(output_dir, 'tmp.html'), 'r') as hocr_file:
                if self.fix_html or character_details:
                    contents = hocr_file.read()
                else:
                    yield hocr_file
                    return
            if character_details:
                worker = ipc.Subprocess(
                    [self.executable, image.name, os.path.join(output_dir, 'tmp'), '-l', language, 'makebox'] + self.extra_args,
                    stderr=ipc.PIPE,
                )
                _wait_for_worker(worker)
                with open(os.path.join(output_dir, 'tmp.box'), 'r') as box_file:
                    contents = contents.replace('</body>', (_bbox_extras_template + '</body>') % cgi.escape(box_file.read()))
        if self.fix_html:
            contents = fix_html(contents)
        with contextlib.closing(StringIO(contents)) as hocr_file:
            yield hocr_file

    def recognize(self, image, language, details=None, uax29=None):
        if self._hocr is None:
            f = self.recognize_plain_text
        else:
            f = self.recognize_hocr
        return f(image, language, details=details, uax29=uax29)

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
