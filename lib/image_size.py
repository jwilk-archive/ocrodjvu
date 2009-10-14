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
Recognize image file formats and size based on their first few bytes.
'''

# Roughly based on Python code provided by Jigloo <phus@live.com>:
# <http://mail.python.org/pipermail/python-list/2007-June/445432.html>.

from cStringIO import StringIO
import struct

__all__ = 'UnknownSize', 'get_image_size'

class UnknownSize(Exception):
    pass

GET_IMAGE_SIZE_DICT = {}

def get_image_size(path):
    file = open(path)
    try:
        chunk = file.read(12)
    finally:
        file.close()
    for head, f in GET_IMAGE_SIZE_DICT.iteritems():
        if chunk.startswith(head):
            file = open(path)
            try:
                return f(file)
            finally:
                file.close()

def header(*values):
    def wrapper(f):
        for value in values:
            GET_IMAGE_SIZE_DICT[value] = f
        return f
    return wrapper

@header(*('P%d' % (i + 1) for i in xrange(6)))
def def_pnm_size(stream):
    head, x, y, tail = stream.read(64).split(None, 3)
    return int(x), int(y)

@header('\xff\xd8')
def get_jpeg_size(stream):
    stream.read(2)
    while True:
        marker, code, length = struct.unpack('>BBH', stream.read(4))
        if marker != 0xff:
            raise UnknownSize('[JPEG] JPEG marker not found')
        elif 0xc0 <= code <= 0xc3:
            y, x = struct.unpack('>xHH', stream.read(5))
            return x, y
        else:
            stream.read(length - 2)
    raise UnknownSize('[JPEG] End of file')

@header('\x89PNG\x0d\x0a\x1a\x0a')
def get_png_size(stream):
    stream.read(12)
    if stream.read(4) == 'IHDR':
        x, y = struct.unpack('>LL', stream.read(8))
        return x, y
    raise UnknownSize('[PNG] IHDR not found')

@header('MM\x00\x2a', 'II\x2a\x00')
def get_tiff_size(stream):
    endian = '>'
    if stream.read(4) == 'II\x2a\x00':
        endian = '<'
    pack_spec = \
    [
        None,
        'Bxxx',
        None,
        endian + 'Hxx',
        endian + 'L',
        None,
        'bxxx',
        None,
        endian + 'hxx',
        endian + 'l'
    ]
    offset, = struct.unpack(endian + 'L', stream.read(4))
    stream.seek(offset, 0)
    n_tags, = struct.unpack(endian + 'H', stream.read(2))
    
    tag = type = 0
    x = y = None
    for i in xrange(n_tags):
        ifd = stream.read(12)
        tag, = struct.unpack(endian + 'H', ifd[:2])
        type, = struct.unpack(endian + 'H', ifd[2 : 2 + 2])
        if type > len(pack_spec) or pack_spec[type] is None:
            continue
        if tag == 0x0100:
            x, = struct.unpack(pack_spec[type], ifd[8 : 4 + 8])
        elif tag == 0x0101:
            y, = struct.unpack(pack_spec[type], ifd[8 : 4 + 8])
        if x and y:
            break
    
    errors = []
    if not x:
        errors += 'Could not determine image width.',
    if not y:
        errors += 'Could not determine image height.',
    if errors:
        raise UnknownSize('[TIFF] ' + ' '.join(errors))
    else:
        return x, y

# vim:ts=4 sw=4 et
