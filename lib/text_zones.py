# encoding=UTF-8

# Copyright © 2008-2015 Jakub Wilk <jwilk@jwilk.net>
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

# On Windows, special measures may be needed to find the DjVuLibre DLL.
try:
    from djvu.dllpath import set_dll_search_path
except ImportError:
    pass
else:  # no coverage
    set_dll_search_path()

from . import utils

try:
    from djvu import const
    from djvu import decode
    from djvu import sexpr
except ImportError as ex:  # no coverage
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
        return '{cls}({0!r}, {1!r}, {2!r}, {3!r})'.format(
            *self._coordinates,
            cls=type(self).__name__
        )

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
        x0, y0, x1, y1 = self.bbox
        if x0 > x1:
            x0, x1 = x1, x0
        elif x0 == x1:
            x1 += 1
        if y0 > y1:
            y0, y1 = y1, y0
        elif y0 == y1:
            y1 += 1
        assert x0 < x1
        assert y0 < y1
        return sexpr.Expression(
            [self.type, x0, y0, x1, y1] +
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
        return '{cls}(type={tp}, bbox={bbox!r}, children={chld!r})'.format(
            cls=type(self).__name__,
            tp=self.type,
            bbox=self.bbox,
            chld=self.children,
        )

    def rotate(self, rotation, xform=None):
        for x in self.bbox:
            assert x is not None
        if xform is None:
            assert self.type == const.TEXT_ZONE_PAGE, (
                'the exterior zone is {tp} rather than {pg}'.format(tp=self.type, pg=const.TEXT_ZONE_PAGE)
            )
            assert self.bbox[:2] == (0, 0), (
                'top-left page corner is ({0}, {1}) rather than (0, 0)'.format(*self.bbox[:2])
            )
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
        del x0, y0, x1, y1  # quieten pyflakes
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
        words += [last_word]
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

try:
    sexpr.Expression(0).as_string(escape_unicode=True)
except TypeError:
    # python-djvulibre << 0.4
    def print_sexpr(expr, file, width=None):
        return expr.print_into(file, width=width)
else:
    # python-djvulibre >= 0.4
    def print_sexpr(expr, file, width=None):
        return expr.print_into(file, width=width, escape_unicode=False)

# vim:ts=4 sts=4 sw=4 et
