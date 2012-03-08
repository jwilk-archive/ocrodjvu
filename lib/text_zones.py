# encoding=UTF-8

# Copyright © 2008, 2009, 2010, 2011, 2012 Jakub Wilk <jwilk@jwilk.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

# On Windows, special measures may be needed to find the DjVuLibre DLL.
try:
    from djvu.dllpath import set_dll_search_path
except ImportError:
    pass
else:
    set_dll_search_path()

from . import utils

try:
    from djvu import const
    from djvu import decode
    from djvu import sexpr
except ImportError, ex:
    utils.enhance_import_error(ex, 'python-djvulibre', 'python-djvu', 'http://jwilk.net/software/python-djvulibre')
    raise

TEXT_DETAILS_LINE = const.TEXT_ZONE_LINE
TEXT_DETAILS_WORD = const.TEXT_ZONE_WORD
TEXT_DETAILS_CHARACTER = const.TEXT_ZONE_CHARACTER

class BBox(object):

    def __init__(self, x0=None, y0=None, x1=None, y1=None):
        self._coordinates = [x0, y0, x1, y1]

    @property
    def x0(self):
        return self[0]

    @property
    def y0(self):
        return self[1]

    @property
    def x1(self):
        return self[2]

    @property
    def y1(self):
        return self[3]

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
        children = [
            child.sexpr if isinstance(child, Zone) else child
            for child in self.children
            if not isinstance(child, Space)
        ] or ['']
        return sexpr.Expression(
            [self.type] +
            list(self.bbox) +
            children
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

    def rotate(self, rotation, xform=None):
        for x in self.bbox:
            assert x is not None
        if xform is None:
            assert self.type == const.TEXT_ZONE_PAGE, 'the exterior zone is %s rather than %s' % (self.type, const.TEXT_ZONE_PAGE)
            assert self.bbox[:2] == (0, 0), 'top-left page corner is (%d, %d) rather than (0, 0)' % self.bbox[:2]
            page_size = self.bbox[2:]
            if (rotation // 90) & 1:
                xform = decode.AffineTransform((0, 0) + tuple(reversed(page_size)), (0, 0) + page_size)
            else:
                xform = decode.AffineTransform((0, 0) + page_size, (0, 0) + page_size)
            xform.mirror_y()
            xform.rotate(rotation)
        x0, y0, x1, y1 = self.bbox
        x0, y0 = xform.inverse((x0, y0))
        x1, y1 = xform.inverse((x1, y1))
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0
        self.bbox = x0, y0, x1, y1
        for child in self:
            if isinstance(child, Zone):
                child.rotate(rotation, xform)

def group_words(zones, details, word_break_iterator):
    text = ''.join(z[0] for z in zones)
    if details > TEXT_DETAILS_WORD:
        # One zone per line
        return [text]
    # One zone per word
    split_zones = []
    for zone in zones:
        zone_text = zone[0]
        if len(zone_text) == 1:
            split_zones += [zone]
            continue
        x0, y0, x1, y1 = zone.bbox
        w = x1 - x0
        m = len(zone_text)
        split_zones += [
            Zone(zone.type, BBox(x0 + w * n // m, y0, x0 + w * (n + 1) // m, y1))
            for n, ch in enumerate(zone_text)
        ]
    zones = split_zones
    del split_zones
    assert len(text) == len(zones)
    words = []
    i = 0
    for j in word_break_iterator(text):
        subtext = text[i:j]
        if subtext.isspace():
            i = j
            continue
        bbox = BBox()
        for k in xrange(i, j):
            bbox.update(zones[k].bbox)
        last_word = Zone(type=const.TEXT_ZONE_WORD, bbox=bbox)
        words += last_word,
        if details > TEXT_DETAILS_CHARACTER:
            last_word += [subtext]
        else:
            last_word += [
                Zone(type=const.TEXT_ZONE_CHARACTER, bbox=(x0, y0, x1, y1), children=[ch])
                for k in xrange(i, j)
                for (x0, y0, x1, y1), ch in [(zones[k].bbox, text[k])]
            ]
        i = j
    return words

# vim:ts=4 sw=4 et
