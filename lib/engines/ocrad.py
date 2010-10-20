# encoding=UTF-8
# Copyright © 2010 Jakub Wilk <jwilk@jwilk.net>
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
import functools
import re

from .. import errors
from .. import image_io
from .. import ipc
from .. import text_zones
from .. import unicode_support

const = text_zones.const

_default_language = 'eng'
_language_pattern = re.compile('^[a-z]{3}$')

def get_languages():
    result = [_default_language]
    try:
        ocrad = ipc.Subprocess(['ocrad', '--charset=help'],
            stdout=ipc.PIPE,
            stderr=ipc.PIPE,
        )
    except OSError:
        raise errors.UnknownLanguageList
    try:
        line = ocrad.stderr.read()
        charsets = set(line.split()[1:])
        if 'iso-8859-9' in charsets:
            result += 'tur',
    finally:
        try:
            ocrad.wait()
        except ipc.CalledProcessError:
            pass
        else:
            raise errors.UnknownLanguageList
    return result

def has_language(language):
    if not _language_pattern.match(language):
        raise errors.InvalidLanguageId(language)
    return language in get_languages()

@contextlib.contextmanager
def recognize(pbm_file, language, details=None):
    charset = 'iso-8859-15'
    if language == 'tur':
        charset = 'iso-8859-9'
    worker = ipc.Subprocess(
        ['ocrad', '--charset', charset, '--format=utf8', '-x', '-', pbm_file.name],
        stdout=ipc.PIPE,
    )
    try:
        yield worker.stdout
    finally:
        worker.wait()

class ExtractSettings(object):

    def __init__(self, rotation=0, details=text_zones.TEXT_DETAILS_WORD, uax29=None, page_size=None):
        self.rotation = rotation
        self.details = details
        if uax29 is not None:
            icu = unicode_support.get_icu()
            if uax29 is True:
                uax29 = icu.Locale()
            else:
                uax29 = icu.Locale(uax29)
        self.uax29 = uax29
        self.page_size = page_size

_character_re = re.compile(r"^[0-9]+, '('|[^']*)'[0-9]+")

def scan(stream, settings):
    word_break_iterator = functools.partial(unicode_support.word_break_iterator, locale=settings.uax29)
    for line in stream:
        if line.startswith('#'):
            continue
        if line.startswith('source '):
            continue
        if line.startswith('total text blocks '):
            [n] = line.split()[3:]
            n = int(n)
            bbox = text_zones.BBox(*((0, 0) + settings.page_size))
            children = filter(None, (scan(stream, settings) for i in xrange(n)))
            zone = text_zones.Zone(const.TEXT_ZONE_PAGE, bbox, children)
            zone.rotate(settings.rotation)
            return zone
        if line.startswith('text block '):
            n, x, y, w, h = map(int, line.split()[2:])
            bbox = text_zones.BBox(x, y, x + w, y + h)
            [children] = [scan(stream, settings) for i in xrange(n)]
            return text_zones.Zone(const.TEXT_ZONE_REGION, bbox, children)
        if line.startswith('lines '):
            [n] = line.split()[1:]
            n = int(n)
            return filter(None, (scan(stream, settings) for i in xrange(n)))
        if line.startswith('line '):
            _, _, _, n, _, _ = line.split()
            n = int(n)
            children = filter(None, (scan(stream, settings) for i in xrange(n)))
            if not children:
                return None
            bbox = text_zones.BBox()
            for child in children:
                bbox.update(child.bbox)
            children = text_zones.group_words(children, settings.details, word_break_iterator)
            return text_zones.Zone(const.TEXT_ZONE_LINE, bbox, children)
        line = line.lstrip()
        if line[0].isdigit():
            coords, line = line.split('; ', 1)
            x, y, w, h = map(int, coords.split())
            bbox = text_zones.BBox(x, y, x + w, y + h)
            if line[0] == '0':
                # No interpretations has been proposed for this particular character.
                text = u'\N{REPLACEMENT CHARACTER}'
                # TODO: Let user to choose another replacement text.
            else:
                m = _character_re.match(line)
                if not m:
                    raise errors.MalformedOcrOutput('bad character description: %r' % line)
                [text] = m.groups()
                text = text.decode('UTF-8')
            return text_zones.Zone(const.TEXT_ZONE_CHARACTER, bbox, [text])
        raise errors.MalformedOcrOutput('unexpected line: %r' % line)
    raise errors.MalformedOcrOutput('unexpected line at EOF: %r' % line)

class Engine(object):

    name = 'ocrad'
    image_format = image_io.PNM
    output_format = 'orf'

    def __init__(self):
        try:
            get_languages()
        except errors.UnknownLanguageList:
            raise errors.EngineNotFound(self.name)

    @staticmethod
    def get_default_language():
        return _default_language

    has_language = staticmethod(has_language)
    list_languages = staticmethod(get_languages)
    recognize = staticmethod(recognize)

    @staticmethod
    def extract_text(stream, **kwargs):
        settings = ExtractSettings(**kwargs)
        scan_result = scan(stream, settings)
        return [scan_result.sexpr]

# vim:ts=4 sw=4 et
