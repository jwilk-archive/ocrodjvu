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

import argparse
import itertools
import locale
import os
import re
import sys

from . import hocr
from . import ipc
from . import utils
from . import version

from .hocr import ET
from .hocr import sexpr
from .hocr import const

__version__ = version.__version__

system_encoding = locale.getpreferredencoding()

class ArgumentParser(argparse.ArgumentParser):

    def __init__(self):
        usage = '%(prog)s [options] FILE'
        version = '%(prog) ' + __version__
        argparse.ArgumentParser.__init__(self, usage=usage, version=version)
        self.add_argument('-p', '--pages', dest='pages', action='store', default=None, help='pages to convert')
        self.add_argument('path', metavar='FILE', help='DjVu file to process')
        group = self.add_argument_group(title='word segmentation options')
        group.add_argument('--word-segmentation', dest='word_segmentation', choices=('simple', 'uax29'), default='space', help='word segmentation algorithm')
        group.add_argument('--language', dest='language', help=argparse.SUPPRESS or 'language for word segmentation', default='eng')
        # This option is currently not very useful, as ICU don't have any specialisations for languages ocrodjvu supports

    def parse_args(self):
        options = argparse.ArgumentParser.parse_args(self)
        try:
            options.pages = utils.parse_page_numbers(options.pages)
        except (TypeError, ValueError):
            self.error('Unable to parse page numbers')
        if options.word_segmentation == 'uax29':
            options.icu = icu = hocr.get_icu()
            options.locale = icu.Locale(options.language)
        else:
            options.icu = None
            options.locale = None
        return options

class CharacterLevelDetails(Exception):
    pass

class Zone(object):

    def __init__(self, sexpr):
        self._sexpr = sexpr

    @property
    def type(self):
        return const.get_text_zone_type(self._sexpr[0].value)

    @property
    def bbox(self):
        return hocr.BBox(*(self._sexpr[i].value for i in xrange(1, 5)))

    @property
    def text(self):
        if len(self._sexpr) != 6:
            raise TypeError
        if not isinstance(self._sexpr[5], sexpr.StringExpression):
            raise TypeError
        return unicode(self._sexpr[5].value, 'UTF-8', 'replace')

    @property
    def children(self):
        for child in self._sexpr[5:]:
            if isinstance(child, sexpr.ListExpression):
                yield Zone(child)
            else:
                yield self.text
                return

    @property
    def n_children(self):
        n = len(self._sexpr) - 5
        if n <= 0:
            raise TypeError
        return n

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, self._sexpr)

_xml_string_re = re.compile(
    u'''
    ([^\x00-\x08\x0b\x0c\x0e-\x1f]*)
    ( [\x00-\x08\x0b\x0c\x0e-\x1f]?)
    ''',
    re.UNICODE | re.VERBOSE
)

def set_text(element, text):
    last = None
    for match in _xml_string_re.finditer(text):
        if match.group(1):
            if last is None:
                element.text = match.group(1)
            else:
                last.tail = match.group(1)
        if match.group(2):
            last = ET.Element('span')
            last.set('class', 'djvu_char')
            last.set('title', '#x%02x' % ord(match.group(2)))
            last.text = ' '
            element.append(last)

def break_chars(char_zone_list, options):
    bbox_list = []
    text = []
    for char_zone in char_zone_list:
        bbox = char_zone.bbox
        char_text = char_zone.text
        if not char_text:
            continue
        for i, char in enumerate(char_text):
            subbox = hocr.BBox(
                int(bbox.x0 + (bbox.x1 - bbox.x0) * 1.0 * i / len(char_text) + 0.5),
                bbox.y0,
                int(bbox.x0 + (bbox.x1 - bbox.x0) * 1.0 * (i + 1) / len(char_text) + 0.5),
                bbox.y1,
            )
            bbox_list += subbox,
        text += char_text,
    text = ''.join(text)
    break_iterator = hocr.word_break_iterator(text, options.locale)
    element = None
    for j in break_iterator:
        subtext = text[i:j]
        if subtext.isspace():
            if element is not None:
                element.tail = ' '
            i = j
            continue
        bbox = hocr.BBox()
        for k in xrange(i, j):
            bbox.update(bbox_list[k])
        element = ET.Element('span')
        element.set('class', 'ocrx_word')
        element.set('title', 'bbox %(bbox)s; bboxes %(bboxes)s' % dict(
            bbox=' '.join(map(str, bbox)),
            bboxes=', '.join(' '.join(map(str, bbox)) for bbox in bbox_list[i:j])
        ))
        set_text(element, subtext)
        yield element
        i = j

def break_plain_text(text, bbox, options):
    icu_text = options.icu.UnicodeString(text)
    break_iterator = options.icu.BreakIterator.createWordInstance(options.locale)
    break_iterator.setText(icu_text)
    i = 0
    element = None
    for j in break_iterator:
        subtext = text[i:j]
        if subtext.isspace():
            if element is not None:
                element.tail = ' '
            i = j
            continue
        subbox = hocr.BBox(
            int(bbox.x0 + (bbox.x1 - bbox.x0) * 1.0 * i / len(text) + 0.5),
            bbox.y0,
            int(bbox.x0 + (bbox.x1 - bbox.x0) * 1.0 * j / len(text) + 0.5),
            bbox.y1,
        )
        element = ET.Element('span')
        element.set('class', 'ocrx_word')
        element.set('title', 'bbox ' + ' '.join(map(str, subbox)))
        set_text(element, subtext)
        yield element
        i = j

def process_zone(parent, parent_zone_type, zone, last, options):
    zone_type = zone.type
    if zone_type <= const.TEXT_ZONE_LINE and parent is not None:
        parent.tail = '\n'
    try:
        hocr_tag, hocr_class = hocr.djvu_zone_to_hocr(zone_type)
    except LookupError, ex:
        if ex[0] == const.TEXT_ZONE_CHARACTER:
            raise CharacterLevelDetails
        raise
    self = ET.Element(hocr_tag)
    self.set('class', hocr_class)
    if zone_type == const.TEXT_ZONE_PAGE:
        bbox = options.page_bbox
    else:
        bbox = zone.bbox
    self.set('title', 'bbox ' + ' '.join(map(str, bbox)))
    n_children = zone.n_children
    character_level_details = False
    for n, child_zone in enumerate(zone.children):
        last_child = n == n_children - 1
        if isinstance(child_zone, Zone):
            try:
                process_zone(self, zone_type, child_zone, last=last_child, options=options)
            except CharacterLevelDetails:
                # Do word segmentation by hand.
                character_level_details = True
                break
    if character_level_details:
        # Do word segmentation by hand.
        child = None
        for child in break_chars(zone.children, options):
            parent.append(child)
        if child is not None and zone_type == const.TEXT_ZONE_WORD and not last:
            child.tail = ' '
        self = None
    elif isinstance(child_zone, unicode):
        text = child_zone
        if zone_type >= const.TEXT_ZONE_WORD and options.icu is not None and parent is not None:
            # Do word segmentation by hand.
            child = None
            for child in break_plain_text(text, bbox, options):
                parent.append(child)
            if child is not None and zone_type == const.TEXT_ZONE_WORD and not last:
                child.tail = ' '
            self = None
        else:
            # Word segmentation as provided by DjVu.
            # There's no point in doing word segmentation if only line coordinates are provided.
            set_text(self, text)
            if zone_type == const.TEXT_ZONE_WORD and not last:
                self.tail = ' '
    if parent is not None and self is not None:
        parent.append(self)
    return self

def process_page(page_text, options):
    result = process_zone(None, None, page_text, last=True, options=options)
    tree = ET.ElementTree(result)
    tree.write(sys.stdout, encoding='UTF-8')

hocr_header = '''\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <title>DjVu hidden text layer</title>
</head>
<body>
'''
hocr_footer = '''
</body>
</html>
'''

def main():
    options = ArgumentParser().parse_args()
    print >>sys.stderr, 'Converting %s:' % utils.smart_repr(options.path, system_encoding)
    if options.pages is None:
        djvused = ipc.Subprocess([
            'djvused', '-e', 'n',
            os.path.abspath(options.path)
        ], stdout=ipc.PIPE)
        try:
            n_pages = int(djvused.stdout.readline())
        finally:
            djvused.wait()
        options.pages = xrange(1, n_pages + 1)
    page_iterator = iter(options.pages)
    sed_script = ''.join('select %d; size; print-txt; ' % n for n in options.pages)
    djvused = ipc.Subprocess([
        'djvused', '-e', sed_script,
        os.path.abspath(options.path),
    ], stdout=ipc.PIPE)
    sys.stdout.write(hocr_header)
    while 1:
        try:
            n = page_iterator.next()
        except StopIteration:
            break
        try:
            page_size = [
                int(str(sexpr.Expression.from_stream(djvused.stdout).value).split('=')[1])
                for i in xrange(2)
            ]
            options.page_bbox = hocr.BBox(0, 0, page_size[0], page_size[1])
            page_text = sexpr.Expression.from_stream(djvused.stdout)
        except sexpr.ExpressionSyntaxError:
            break
        print >>sys.stderr, '- Page #%d' % n
        process_page(Zone(page_text), options)
    sys.stdout.write(hocr_footer)
    djvused.wait()

# vim:ts=4 sw=4 et
