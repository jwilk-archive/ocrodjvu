# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

'''
Process hOCR documents.

The hOCR format specification:
http://docs.google.com/Doc?id=dfxcv4vc_67g844kf
'''

import re

try:
    import lxml.etree as ET
except ImportError, ex:
    ex.args = '%s; please install the lxml package <http://codespeak.net/lxml/>' % str(ex),
    raise

try:
    from djvu import sexpr
    from djvu import const
    from djvu import decode
except ImportError, ex:
    ex.args = '%s; please install the python-djvulibre package <http://jwilk.net/software/python-djvulibre.html>' % str(ex),
    raise

from . import image_size
from . import errors

__all__ = 'extract_text', 'TEXT_DETAILS_LINE', 'TEXT_DETAILS_WORD', 'TEXT_DETAILS_CHARACTER'

TEXT_DETAILS_LINE = const.TEXT_ZONE_LINE
TEXT_DETAILS_WORD = const.TEXT_ZONE_WORD
TEXT_DETAILS_CHARACTER = const.TEXT_ZONE_CHARACTER

hocr_class_to_djvu = \
dict(
    ocr_page = const.TEXT_ZONE_PAGE,
    ocr_column = const.TEXT_ZONE_COLUMN,
    ocr_carea = const.TEXT_ZONE_COLUMN,
    ocr_par = const.TEXT_ZONE_PARAGRAPH,
    ocr_line = const.TEXT_ZONE_LINE,
    ocrx_block = const.TEXT_ZONE_REGION,
    ocrx_line = const.TEXT_ZONE_LINE,
    ocrx_word = const.TEXT_ZONE_WORD
).get

djvu_zone_to_hocr = {
    const.TEXT_ZONE_PAGE: ('div', 'ocr_page'),
    const.TEXT_ZONE_COLUMN: ('div', 'ocr_carea'),
    const.TEXT_ZONE_PARAGRAPH: ('p', 'ocr_par'),
    const.TEXT_ZONE_REGION: ('span', 'ocrx_block'),
    const.TEXT_ZONE_LINE: ('span', 'ocrx_line'),
    const.TEXT_ZONE_WORD: ('span', 'ocrx_word'),
}.__getitem__

IMAGE_RE = re.compile(
    r'''
        image \s+ (?P<file_name> \S+)
    ''', re.VERBOSE)

BBOX_RE = re.compile(
    r'''
        bbox \s+
        (?P<x0> -?\d+) \s+
        (?P<y0> -?\d+) \s+
        (?P<x1> -?\d+) \s+
        (?P<y1> -?\d+)
    ''', re.VERBOSE)

BBOXES_RE = re.compile(
    r'''
        bboxes \s+
        (         (?: \d+ \s+ \d+ \s+ \d+ \s+ \d+)
        (?: , \s* (?: \d+ \s+ \d+ \s+ \d+ \s+ \d+) )* )
    ''', re.VERBOSE)

class BBox(object):

    def __init__(self, x0=None, y0=None, x1=None, y1=None):
        self._coordinates = [x0, y0, x1, y1]
    
    @property
    def x0(self): return self[0]

    @property
    def y0(self): return self[1]

    @property
    def x1(self): return self[2]

    @property
    def y1(self): return self[3]

    def __getitem__(self, item):
        return self._coordinates[item]

    def __nonzero__(self):
        for value in self._coordinates:
            if value is None:
                return False
        return True
    
    def __repr__(self):
        return '%s(%r, %r, %r, %r)' % ((self.__class__.__name__,) + tuple(self._coordinates))

    def update(self, bbox):
        for i, self_i in enumerate(self._coordinates):
            if self_i is None:
                self._coordinates[i] = bbox[i]
            elif i < 2 and bbox[i] is not None and self[i] > bbox[i]:
                self._coordinates[i] = bbox[i]
            elif i > 1 and bbox[i] is not None and self[i] < bbox[i]:
                self._coordinates[i] = bbox[i]

def get_icu():
    try:
        import PyICU
    except ImportError, ex:
        ex.args = '%s; please install the PyICU package <http://pyicu.osafoundation.org/>' % str(ex),
        raise
    return PyICU

def simple_word_break_iterator(text):
    '''
    Create an instance of simple space-to-space word break interator.
    '''
    if not text:
        return
    space = text[0].isspace()
    for n, ch in enumerate(text):
        if space != ch.isspace():
            yield n
            space = not space
    yield len(text)

def word_break_iterator(text, locale=None):
    '''
    Create an instance of word break interator.

    text: unicode string
    locale: ICU locale or None
    '''
    if locale is None:
        return simple_word_break_iterator(text)
    icu = get_icu()
    break_iterator = icu.BreakIterator.createWordInstance(locale)
    icu_text = icu.UnicodeString(text)
    break_iterator.setText(text)
    return break_iterator

def _replace_text(djvu_class, title, text, settings):
    if djvu_class <= const.TEXT_ZONE_LINE:
        text = text.rstrip('\n')
    if settings.details >= djvu_class:
        return text,
    m = BBOXES_RE.search(title)
    if not m:
        return text,
    coordinates = [map(int, bbox.strip().split()) for bbox in m.group(1).split(',')]
    if len(coordinates) == len(text):
        pass # OK
    elif len(coordinates) == len(text) + 1:
        # FIXME: This is not OK, user should be warned.
        # Continue anyway.
        del coordinates[-1]
        pass
    else:
        # FIXME: This is not OK, user should be warned.
        return [text]
    if djvu_class > const.TEXT_ZONE_WORD:
        # Split words
        words = []
        break_iterator = word_break_iterator(text, locale=settings.uax29)
        i = 0
        for j in break_iterator:
            subtext = text[i:j]
            if subtext.isspace():
                i = j
                continue
            bbox = BBox()
            for k in xrange(i, j):
                bbox.update(BBox(*coordinates[k]))
            last_word = [const.TEXT_ZONE_WORD] + list(bbox)
            words += last_word,
            if settings.details > const.TEXT_ZONE_CHARACTER:
                last_word += subtext,
            else:
                last_word += [
                    [const.TEXT_ZONE_CHARACTER, x0, y0, x1, y1, ch]
                    for k in xrange(i, j)
                    for (x0, y0, x1, y1), ch in [(coordinates[k], text[k])]
                ]
            i = j
        return words
    else:
        # Split characters
        return [
            (const.TEXT_ZONE_CHARACTER, x0, y0, x1, y1, ch)
            for (x0, y0, x1, y1), ch in zip(coordinates, text)
        ]
    return text,

def _rotate(obj, rotation, xform=None):
    if xform is None:
        assert len(obj) >= 5
        assert obj[0] == const.TEXT_ZONE_PAGE
        assert obj[1] == obj[2] == 0
        page_width, page_height = page_size = (obj[3], obj[4])
        if (rotation // 90) & 1:
             page_width, page_height = page_size
             xform = decode.AffineTransform((0, 0, page_height, page_width), (0, 0) + page_size)
        else:
            xform = decode.AffineTransform((0, 0) + page_size, (0, 0) + page_size)
        xform.mirror_y()
        xform.rotate(rotation)
    x0, y0, x1, y1 = obj[1:5]
    x0, y0 = xform.inverse((x0, y0))
    x1, y1 = xform.inverse((x1, y1))
    obj[1:5] = x0, y0, x1, y1
    for child in obj:
        if isinstance(child, list):
            _rotate(child, rotation, xform)
        elif isinstance(child, (sexpr.Symbol, int, basestring)):
            pass
        else:
            raise TypeError('%r in not in: list, int, basestring, Symbol' % type(child).__name__)

def _scan(node, buffer, parent_bbox, page_size, settings):
    def look_down(buffer, parent_bbox):
        for child in node.iterchildren():
            _scan(child, buffer, parent_bbox, page_size, settings)
            if node.tail and node.tail.strip():
                buffer.append(node.tail)
        if node.text and node.text.strip():
            buffer.append(node.text)
    if not isinstance(node.tag, basestring):
        return
    hocr_classes = (node.get('class') or '').split()
    djvu_class = None
    for hocr_class in hocr_classes:
        djvu_class = hocr_class_to_djvu(hocr_class)
        if djvu_class:
            break
    else:
        look_down(buffer, parent_bbox)
        return
    title = node.get('title') or ''
    m = BBOX_RE.search(title)
    if m is None:
        bbox = BBox()
    else:
        bbox = BBox(*(int(m.group(id)) for id in ('x0', 'y0', 'x1', 'y1')))
        parent_bbox.update(bbox)
    if djvu_class is const.TEXT_ZONE_PAGE:
        if not bbox:
            m = IMAGE_RE.search(title)
            if m is None:
                raise errors.MalformedHocr("cannot determine page's bbox")
            page_size = image_size.get_image_size(m.group('file_name'))
            page_width, page_height = page_size
            bbox = BBox(0, 0, page_width - 1, page_height - 1)
            parent_bbox.update(bbox)
        else:
            if (bbox.x0, bbox.y0) != (0, 0):
                raise errors.MalformedHocr("page's bbox should start with (0, 0)")
            page_size = bbox.x1, bbox.y1
    result = [sexpr.Symbol(djvu_class)]
    result += [None] * 4
    look_down(result, bbox)
    if isinstance(result[-1], basestring):
        result[-1:] = _replace_text(djvu_class, title, result[-1], settings)
    if not bbox and not len(node):
        return
    if page_size is None:
        raise errors.MalformedHocr('unable to determine page size')
    result[1], result[2], result[3], result[4] = bbox
    if len(result) == 5:
        result.append('')
    buffer.append(result)

def scan(node, settings):
    buffer = []
    _scan(node, buffer, BBox(), None, settings)
    for obj in buffer:
        _rotate(obj, settings.rotation)
    return buffer

class ExtractSettings(object):

    def __init__(self, rotation=0, details=TEXT_DETAILS_WORD, uax29=None):
        self.rotation = rotation
        self.details = details
        if uax29 is not None:
            icu = get_icu()
            if uax29 is True:
                uax29 = icu.Locale()
            else:
                uax29 = icu.Locale(uax29)
        self.uax29 = uax29

def extract_text(stream, **kwargs):
    '''
    Extract DjVu text from an hOCR stream.

    details: TEXT_DETAILS_LINES or TEXT_DETAILS_WORD or TEXT_DETAILS_CHAR
    uax29: None or a PyICU locale
    '''
    settings = ExtractSettings(**kwargs)
    doc = ET.parse(stream, ET.HTMLParser())
    scan_result = scan(doc.find('/body'), settings)
    return sexpr.Expression(scan_result)

# vim:ts=4 sw=4 et
