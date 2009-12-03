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

from image_size import get_image_size

__all__ = 'extract_text', 'TEXT_DETAILS_LINE', 'TEXT_DETAILS_WORD', 'TEXT_DETAILS_CHARACTER'

from djvu.decode import TEXT_DETAILS_LINE, TEXT_DETAILS_WORD, TEXT_DETAILS_CHARACTER

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

IMAGE_RE = re.compile(
    r'''
        image \s+ (?P<file_name> \S+)
    ''', re.VERBOSE)

BBOX_RE = re.compile(
    r'''
        bbox \s+
        (?P<x0> \d+) \s+ 
        (?P<y0> \d+) \s+
        (?P<x1> \d+) \s+
        (?P<y1> \d+)
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

def _scan(node, buffer, parent_bbox, page_size=None, rotation=0):
    def look_down(buffer, parent_bbox):
        for child in node.iterchildren():
            _scan(child, buffer, parent_bbox, page_size, rotation)
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
    if djvu_class:
        title = node.get('title') or ''
        m = BBOX_RE.search(title)
        if m is None:
            bbox = BBox()
        else:
            bbox = BBox(*(int(m.group(id)) for id in ('x0', 'y0', 'x1', 'y1')))
            parent_bbox.update(bbox)
    if djvu_class:
        if djvu_class is const.TEXT_ZONE_PAGE:
            if not bbox:
                m = IMAGE_RE.search(title)
                if m is None:
                    raise Exception("Cannot determine page's bbox")
                page_size = get_image_size(m.group('file_name'))
                page_width, page_height = page_size
                bbox = BBox(0, 0, page_width - 1, page_height - 1)
                parent_bbox.update(bbox)
            else:
                if (bbox.x0, bbox.y0) != (0, 0):
                    raise Exception("Page's bbox should start with (0, 0)")
                page_size = bbox.x1, bbox.y1
        result = [sexpr.Symbol(djvu_class)]
        result += [None] * 4
        look_down(result, bbox)
        if not bbox and not len(node):
            return
        if page_size is None:
            raise Exception('Unable to determine page size')
        if (rotation / 90) & 1:
            page_width, page_height = page_size
            xform = decode.AffineTransform((0, 0, page_height, page_width), (0, 0) + page_size)
        else:
            xform = decode.AffineTransform((0, 0) + page_size, (0, 0) + page_size)
        xform.mirror_y()
        xform.rotate(rotation)
        x0, y0, x1, y1 = bbox
        x0, y0 = xform.inverse((x0, y0))
        x1, y1 = xform.inverse((x1, y1))
        result[1] = x0
        result[2] = y0
        result[3] = x1
        result[4] = y1
        if len(result) == 5:
            result.append('')
        buffer.append(result)
    else:
        look_down(buffer, parent_bbox)

def scan(node, rotation=0):
    buffer = []
    _scan(node, buffer, BBox(), rotation=rotation)
    return buffer

def extract_text(stream, rotation=0, details=TEXT_DETAILS_WORD):
    '''
    Extract DjVu text from an hOCR stream.
    '''
    doc = ET.parse(stream, ET.HTMLParser())
    scan_result = scan(doc.find('/body'), rotation=rotation)
    return sexpr.Expression(scan_result)

# vim:ts=4 sw=4 et
