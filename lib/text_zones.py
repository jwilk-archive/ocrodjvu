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

try:
    from djvu import const
    from djvu import decode
    from djvu import sexpr
except ImportError, ex:
    ex.args = '%s; please install the python-djvulibre package <http://jwilk.net/software/python-djvulibre>' % str(ex),
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

    def rotate(obj, rotation, xform=None):
        if xform is None:
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
                child.rotate(rotation, xform)

# vim:ts=4 sw=4 et
