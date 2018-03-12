# encoding=UTF-8

# Copyright © 2009-2018 Jakub Wilk <jwilk@jwilk.net>
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

from __future__ import print_function

import argparse
import cgi
import locale
import os
import re
import sys

from .. import cli
from .. import hocr
from .. import ipc
from .. import logger
from .. import temporary
from .. import text_zones
from .. import unicode_support
from .. import utils
from .. import version

from ..hocr import etree
from ..text_zones import const
from ..text_zones import sexpr

__version__ = version.__version__

system_encoding = locale.getpreferredencoding()

logger = logger.setup()

class ArgumentParser(cli.ArgumentParser):

    def __init__(self):
        usage = '%(prog)s [options] FILE'
        cli.ArgumentParser.__init__(self, usage=usage)
        self.add_argument('--version', action=version.VersionAction)
        group = self.add_argument_group(title='input selection options')
        group.add_argument('path', metavar='FILE', help='DjVu file to covert')
        def pages(x):
            return utils.parse_page_numbers(x)
        group.add_argument('-p', '--pages', dest='pages', action='store', default=None, type=pages, help='pages to convert')
        group = self.add_argument_group(title='word segmentation options')
        group.add_argument('--word-segmentation', dest='word_segmentation', choices=('simple', 'uax29'), default='simple', help='word segmentation algorithm')
        # -l/--language is currently not very useful, as ICU don't have any specialisations for languages ocrodjvu supports:
        group.add_argument('-l', '--language', dest='language', help=argparse.SUPPRESS or 'language for word segmentation', default='eng')
        group = self.add_argument_group(title='HTML output options')
        group.add_argument('--title', dest='title', help='document title', default='DjVu hidden text layer')
        group.add_argument('--css', metavar='STYLE', dest='css', help='CSS style', default='')

    def parse_args(self, args=None, namespace=None):
        options = cli.ArgumentParser.parse_args(self, args, namespace)
        if options.word_segmentation == 'uax29':
            options.icu = icu = unicode_support.get_icu()
            options.locale = icu.Locale(options.language)
        else:
            options.icu = None
            options.locale = None
        return options

class CharacterLevelDetails(Exception):
    pass

class Zone(object):

    def __init__(self, sexpr, page_height):
        self._sexpr = sexpr
        self._page_height = page_height

    @property
    def type(self):
        return const.get_text_zone_type(self._sexpr[0].value)

    @property
    def bbox(self):
        return text_zones.BBox(
            self._sexpr[1].value,
            self._page_height - self._sexpr[4].value,
            self._sexpr[3].value,
            self._page_height - self._sexpr[2].value,
        )

    @property
    def text(self):
        if len(self._sexpr) != 6:
            raise TypeError('list of {0} (!= 6) elements'.format(len(self._sexpr)))  # no coverage
        if not isinstance(self._sexpr[5], sexpr.StringExpression):
            raise TypeError('last element is not a string')  # no coverage
        return unicode(self._sexpr[5].value, 'UTF-8', 'replace')

    @property
    def children(self):
        for child in self._sexpr[5:]:
            if isinstance(child, sexpr.ListExpression):
                yield Zone(child, self._page_height)
            else:
                yield self.text
                return

    @property
    def n_children(self):
        n = len(self._sexpr) - 5
        if n <= 0:
            raise TypeError('list of {0} (< 6) elements'.format(len(self._sexpr)))  # no coverage
        return n

    def __repr__(self):
        return '{tp}({sexpr!r})'.format(tp=type(self).__name__, sexpr=self._sexpr)

_xml_string_re = re.compile(
    u'''
    ([^\x00-\x08\x0B\x0C\x0E-\x1F]*)
    ( [\x00-\x08\x0B\x0C\x0E-\x1F]?)
    ''',
    re.VERBOSE
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
            last = etree.Element('span')
            last.set('class', 'djvu_char')
            last.set('title', '#x{0:02x}'.format(ord(match.group(2))))
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
            subbox = text_zones.BBox(
                int(bbox.x0 + (bbox.x1 - bbox.x0) * 1.0 * i / len(char_text) + 0.5),
                bbox.y0,
                int(bbox.x0 + (bbox.x1 - bbox.x0) * 1.0 * (i + 1) / len(char_text) + 0.5),
                bbox.y1,
            )
            bbox_list += [subbox]
        text += [char_text]
    text = ''.join(text)
    break_iterator = unicode_support.word_break_iterator(text, options.locale)
    element = None
    i = 0
    for j in break_iterator:
        subtext = text[i:j]
        if subtext.isspace():
            if element is not None:
                element.tail = ' '
            i = j
            continue
        bbox = text_zones.BBox()
        for k in xrange(i, j):
            bbox.update(bbox_list[k])
        element = etree.Element('span')
        element.set('class', 'ocrx_word')
        element.set('title', 'bbox {bbox}; bboxes {bboxes}'.format(
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
        subbox = text_zones.BBox(
            int(bbox.x0 + (bbox.x1 - bbox.x0) * 1.0 * i / len(text) + 0.5),
            bbox.y0,
            int(bbox.x0 + (bbox.x1 - bbox.x0) * 1.0 * j / len(text) + 0.5),
            bbox.y1,
        )
        element = etree.Element('span')
        element.set('class', 'ocrx_word')
        element.set('title', 'bbox ' + ' '.join(map(str, subbox)))
        set_text(element, subtext)
        yield element
        i = j

def process_zone(parent, zone, last, options):
    zone_type = zone.type
    if zone_type <= const.TEXT_ZONE_LINE and parent is not None:
        parent.tail = '\n'
    try:
        hocr_tag, hocr_class = hocr.djvu_zone_to_hocr(zone_type)
    except LookupError as ex:
        if ex[0] == const.TEXT_ZONE_CHARACTER:
            raise CharacterLevelDetails
        raise
    self = etree.Element(hocr_tag)
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
                process_zone(self, child_zone, last=last_child, options=options)
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
    result = process_zone(None, page_text, last=True, options=options)
    tree = etree.ElementTree(result)
    tree.write(sys.stdout, encoding='UTF-8')

hocr_header_template = '''\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="ocr-system" content="{ocr_system}" />
  <meta name="ocr-capabilities" content="{ocr_capabilities}" />
  <style type="text/css">{css}</style>
  <title>{title}</title>
</head>
<body>
'''

hocr_header_style_re = re.compile(r'^\s+<style\s.*?\n', re.MULTILINE)

hocr_footer = '''
</body>
</html>
'''

def main(argv=sys.argv):
    options = ArgumentParser().parse_args(argv[1:])
    logger.info('Converting {path}:'.format(path=utils.smart_repr(options.path, system_encoding)))
    if options.pages is None:
        djvused = ipc.Subprocess(
            ['djvused', '-e', 'n', os.path.abspath(options.path)],
            stdout=ipc.PIPE,
        )
        try:
            n_pages = int(djvused.stdout.readline())
        finally:
            djvused.wait()
        options.pages = xrange(1, n_pages + 1)
    page_iterator = iter(options.pages)
    sed_script = temporary.file(suffix='.djvused')
    for n in options.pages:
        print('select {0}; size; print-txt'.format(n), file=sed_script)
    sed_script.flush()
    djvused = ipc.Subprocess(
        ['djvused', '-f', sed_script.name, os.path.abspath(options.path)],
        stdout=ipc.PIPE,
    )
    ocr_system = 'djvu2hocr {ver}'.format(ver=__version__)
    hocr_header = hocr_header_template.format(
        ocr_system=ocr_system,
        ocr_capabilities=' '.join(hocr.djvu2hocr_capabilities),
        title=cgi.escape(options.title),
        css=cgi.escape(options.css),
    )
    if not options.css:
        hocr_header = re.sub(hocr_header_style_re, '', hocr_header, count=1)
    sys.stdout.write(hocr_header)
    for n in page_iterator:
        try:
            page_size = [
                int(str(sexpr.Expression.from_stream(djvused.stdout).value).split('=')[1])
                for i in xrange(2)
            ]
            options.page_bbox = text_zones.BBox(0, 0, page_size[0], page_size[1])
            page_text = sexpr.Expression.from_stream(djvused.stdout)
        except sexpr.ExpressionSyntaxError:
            break
        logger.info('- Page #{n}'.format(n=n))
        page_zone = Zone(page_text, page_size[1])
        process_page(page_zone, options)
    sys.stdout.write(hocr_footer)
    djvused.wait()

# vim:ts=4 sts=4 sw=4 et
