# encoding=UTF-8
# Copyright © 2008, 2009, 2010 Jakub Wilk <jwilk@jwilk.net>
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
    from lxml import etree
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

cuneiform_tag_to_djvu = \
dict(
    body = const.TEXT_ZONE_PAGE,
    p = const.TEXT_ZONE_PARAGRAPH,
    span = const.TEXT_ZONE_CHARACTER,
).get

_djvu_zone_to_hocr = {
    const.TEXT_ZONE_PAGE: ('div', 'ocr_page'),
    const.TEXT_ZONE_COLUMN: ('div', 'ocr_carea'),
    const.TEXT_ZONE_PARAGRAPH: ('p', 'ocr_par'),
    const.TEXT_ZONE_REGION: ('span', 'ocrx_block'),
    const.TEXT_ZONE_LINE: ('span', 'ocrx_line'),
    const.TEXT_ZONE_WORD: ('span', 'ocrx_word'),
}
djvu2hocr_capabilities = list(sorted(cls for tag, cls in _djvu_zone_to_hocr.itervalues()))
djvu_zone_to_hocr = _djvu_zone_to_hocr.__getitem__
del _djvu_zone_to_hocr

image_re = re.compile(
    r'''
        image \s+ (?P<file_name> \S+)
    ''', re.VERBOSE)

bbox_re = re.compile(
    r'''
        bbox \s+
        (?P<x0> -?\d+) \s+
        (?P<y0> -?\d+) \s+
        (?P<x1> -?\d+) \s+
        (?P<y1> -?\d+)
    ''', re.VERBOSE)

bboxes_re = re.compile(
    r'''
        bboxes \s+
        (          (?: -?\d+ \s+ -?\d+ \s+ -?\d+ \s+ -?\d+)
        (?: ,? \s* (?: -?\d+ \s+ -?\d+ \s+ -?\d+ \s+ -?\d+) )* )
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

class Space(object):
    pass

class Zone(object):

    def __init__(self, type, bbox=None, children=()):
        self.type = type
        self.bbox = bbox
        self.children = list(children)

    def set_bbox(self, bbox):
        if bbox is None:
            self._bbox = None
        else:
            self._bbox = tuple(bbox)

    def get_bbox(self):
        return self._bbox 

    bbox = property(get_bbox, set_bbox)

    @property
    def sexpr(self):
        return sexpr.Expression(
            [self.type] +
            list(self.bbox) + [
                child.sexpr if isinstance(child, Zone) else child
                for child in self.children
                if not isinstance(child, Space)
            ]
        )

    def __iter__(self):
        return iter(self.children)

    def __iadd__(self, new_children):
        self.children += new_children
        return self

    def __getitem__(self, n):
        return self.children[n]

    def __setitem__(self, n, value):
        self.children[n] = value

    def __len__(self):
        return len(self.children)

    def __repr__(self):
        return '%(name)s(type=%(type)r, bbox=%(bbox)r, children=%(children)r)' % dict(
            name=type(self).__name__,
            type=self.type,
            bbox=self.bbox,
            children=self.children,
        )

def _replace_cuneiform08_paragraph(paragraph, settings):
    text = ''.join(
        ' ' if isinstance(character, Space) else character[0]
        for character in paragraph
    )
    if settings.details >= const.TEXT_ZONE_LINE:
        # Cuneiform tends to attach superfluous whitespace:
        text = text.rstrip()
        return [text]
    if len(text) != len(paragraph):
        raise errors.MalformedHocr("number of bboxes doesn't match text length")
    break_iterator = word_break_iterator(text, locale=settings.uax29)
    i = 0
    words = Zone(type=const.TEXT_ZONE_PARAGRAPH)
    paragraph_bbox = BBox()
    for j in break_iterator:
        subtext = text[i:j]
        if subtext.isspace():
            i = j
            continue
        word_bbox = BBox()
        for k in xrange(i, j):
            word_bbox.update(BBox(*paragraph[k].bbox))
        paragraph_bbox.update(word_bbox)
        last_word = Zone(type=const.TEXT_ZONE_WORD, bbox=word_bbox)
        words += last_word,
        if settings.details > const.TEXT_ZONE_CHARACTER:
            last_word += subtext,
        else:
            last_word += paragraph[i:j]
        i = j
    words.bbox = paragraph_bbox
    return words

def _replace_text(djvu_class, title, text, settings):
    embedded_eol = False
    if djvu_class <= const.TEXT_ZONE_LINE:
        if text.endswith('\n'):
            embedded_eol = True
            text = text[:-1]
    if settings.cuneiform:
        # Cuneiform tends to attach superfluous whitespace:
        text = text.rstrip()
    if settings.details >= djvu_class:
        return text,
    m = bboxes_re.search(title)
    if not m:
        return text,
    coordinates = (int(x) for x in m.group(1).replace(',', ' ').split())
    coordinates = zip(coordinates, coordinates, coordinates, coordinates)
    if len(coordinates) == len(text):
        pass # OK
    else:
        if not embedded_eol and len(coordinates) == len(text) + 1:
            # OCRopus produces weird hOCR output if line ends with a hyphen
            del coordinates[-1]
        else:
            raise errors.MalformedHocr("number of bboxes doesn't match text length")
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
            last_word = Zone(type=const.TEXT_ZONE_WORD, bbox=bbox)
            words += last_word,
            if settings.details > const.TEXT_ZONE_CHARACTER:
                last_word += subtext,
            else:
                last_word += [
                    Zone(type=const.TEXT_ZONE_CHARACTER, bbox=(x0, y0, x1, y1), children=[ch])
                    for k in xrange(i, j)
                    for (x0, y0, x1, y1), ch in [(coordinates[k], text[k])]
                ]
            i = j
        return words
    else:
        # Split characters
        return [
            Zone(type=const.TEXT_ZONE_CHARACTER, bbox=(x0, y0, x1, y1), children=[ch])
            for (x0, y0, x1, y1), ch in zip(coordinates, text)
        ]
    return text,

def _rotate(obj, rotation, xform=None):
    if xform is None:
        assert isinstance(obj, Zone)
        assert obj.type == const.TEXT_ZONE_PAGE
        assert obj.bbox[:2] == (0, 0)
        page_size = obj.bbox[2:]
        if (rotation // 90) & 1:
            xform = decode.AffineTransform((0, 0) + tuple(reversed(page_size)), (0, 0) + page_size)
        else:
            xform = decode.AffineTransform((0, 0) + page_size, (0, 0) + page_size)
        xform.mirror_y()
        xform.rotate(rotation)
    x0, y0, x1, y1 = obj.bbox
    x0, y0 = xform.inverse((x0, y0))
    x1, y1 = xform.inverse((x1, y1))
    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0
    obj.bbox = x0, y0, x1, y1
    for child in obj:
        if isinstance(child, Zone):
            _rotate(child, rotation, xform)

def _scan(node, buffer, parent_bbox, settings):
    def look_down(buffer, parent_bbox):
        for child in node.iterchildren():
            _scan(child, buffer, parent_bbox, settings)
            if child.tail:
                if child.tail.strip():
                    buffer += child.tail,
                else:
                    buffer += Space(),
        if node.text and node.text.strip():
            buffer += node.text,
    if not isinstance(node.tag, basestring):
        return
    if settings.cuneiform and settings.cuneiform <= (0, 8):
        # Cuneiform ≤ 0.8 don't mark OCR elements in a hOCR way:
        djvu_class = cuneiform_tag_to_djvu(node.tag)
    else:
        hocr_classes = (node.get('class') or '').split()
        djvu_class = None
        for hocr_class in hocr_classes:
            djvu_class = hocr_class_to_djvu(hocr_class)
            if djvu_class:
                break
        else:
            if node.tag == 'p':
                # Cuneiform ≥ 0.9 don't mark paragraphs in a hOCR way:
                djvu_class = cuneiform_tag_to_djvu(node.tag)
    if not djvu_class:
        look_down(buffer, parent_bbox)
        return
    title = node.get('title') or ''
    m = bbox_re.search(title)
    if m is None:
        bbox = BBox()
    else:
        bbox = BBox(*(int(m.group(id)) for id in ('x0', 'y0', 'x1', 'y1')))
        parent_bbox.update(bbox)
    if bbox.x0 == bbox.y0 == bbox.x1 == bbox.y1 == 0:
        # Skip empty fragments generated by Cuneiform 0.9:
        return
    if djvu_class is const.TEXT_ZONE_PAGE:
        if not bbox:
            if settings.page_size is None:
                m = image_re.search(title)
                if m is None:
                    raise errors.MalformedHocr("cannot determine page's bbox")
                settings.page_size = image_size.get_image_size(m.group('file_name'))
            page_width, page_height = settings.page_size
            bbox = BBox(0, 0, page_width, page_height)
            parent_bbox.update(bbox)
        else:
            if (bbox.x0, bbox.y0) != (0, 0):
                raise errors.MalformedHocr("page's bbox should start with (0, 0)")
            settings.page_size = bbox.x1, bbox.y1
    result = Zone(type=djvu_class)
    look_down(result, bbox)
    if bbox.x0 == bbox.y0 == bbox.x1 == bbox.y1 == 0:
        # Skip empty fragments generated by Cuneiform 0.9:
        return
    if len(result) > 0 and isinstance(result[-1], basestring):
        if settings.cuneiform and settings.cuneiform == (0, 9):
            # hOCR produced by Cuneiform 0.9 is really awkward, let's work
            # around this.
            bboxes_node = node.find('span[@class="ocr_cinfo"]')
            if bboxes_node is not None and len(bboxes_node) == 0 and bboxes_node.text is None:
                title = bboxes_node.get('title') or ''
        result[-1:] = _replace_text(djvu_class, title, result[-1], settings)
    elif settings.cuneiform and settings.cuneiform <= (0, 8) and djvu_class is const.TEXT_ZONE_PARAGRAPH:
        result[:] = _replace_cuneiform08_paragraph(result[:], settings)
    if not bbox and not len(node):
        return
    if settings.page_size is None:
        raise errors.MalformedHocr('unable to determine page size')
    result.bbox = bbox
    if len(result) == 0:
        result += '',
    buffer += result,

def scan(node, settings):
    buffer = []
    _scan(node, buffer, BBox(), settings)
    # Buffer may contain also superfluous Space objects. Let's strip them.
    buffer = [zone for zone in buffer if isinstance(zone, Zone)]
    for zone in buffer:
        _rotate(zone, settings.rotation)
    return buffer

class ExtractSettings(object):

    def __init__(self, rotation=0, details=TEXT_DETAILS_WORD, uax29=None, page_size=None, cuneiform=None):
        self.rotation = rotation
        self.details = details
        if uax29 is not None:
            icu = get_icu()
            if uax29 is True:
                uax29 = icu.Locale()
            else:
                uax29 = icu.Locale(uax29)
        self.uax29 = uax29
        self.page_size = page_size
        self.cuneiform = cuneiform

def extract_text(stream, **kwargs):
    '''
    Extract DjVu text from an hOCR stream.

    details: TEXT_DETAILS_LINES or TEXT_DETAILS_WORD or TEXT_DETAILS_CHAR
    uax29: None or a PyICU locale
    '''
    settings = ExtractSettings(**kwargs)
    doc = etree.parse(stream, etree.HTMLParser())
    if doc.find('/head/meta[@name="ocr-capabilities"]') is None:
        ocr_system = doc.find('/head/meta[@name="ocr-system"]')
        if ocr_system is not None and ocr_system.get('content') == 'openocr':
            settings.cuneiform = (0, 9)
        else:
            # Wild guess:
            settings.cuneiform = (0, 8)
    scan_result = scan(doc.find('/body'), settings)
    return [zone.sexpr for zone in scan_result]

# vim:ts=4 sw=4 et
