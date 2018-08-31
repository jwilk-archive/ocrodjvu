# encoding=UTF-8

# Copyright © 2008-2018 Jakub Wilk <jwilk@jwilk.net>
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

import struct

from . import utils

try:
    import djvu.decode
except ImportError as ex:
    utils.enhance_import_error(ex, 'python-djvulibre', 'python-djvu', 'http://jwilk.net/software/python-djvulibre')
    raise

class ImageFormat(object):

    extension = None

    _rgb = 'RGB'

    def __init__(self, bpp):
        self.bpp = bpp
        if bpp == 1:
            pixel_format = djvu.decode.PixelFormatPackedBits('>')
            pixel_format.rows_top_to_bottom = 1
            pixel_format.y_top_to_bottom = 1
        elif bpp == 24:
            pixel_format = djvu.decode.PixelFormatRgb(self._rgb)
            pixel_format.rows_top_to_bottom = 1
            pixel_format.y_top_to_bottom = 1
        else:
            raise NotImplementedError('Cannot output {0}-bpp images'.format(bpp))
        self._pixel_format = pixel_format

    @utils.not_overridden
    def write_image(self, page_job, render_layers, file):
        raise NotImplementedError('Cannot output images in this format')

    def __repr__(self):
        return '{mod}.{cls}({bpp})'.format(mod=self.__module__, cls=type(self).__name__, bpp=self.bpp)

class PNM(ImageFormat):

    '''
    Raw PBM[0] or raw PPM[1].

    [0] http://netpbm.sourceforge.net/doc/ppm.html
    [1] http://netpbm.sourceforge.net/doc/pbm.html
    '''

    extension = 'pnm'

    def __init__(self, bpp):
        ImageFormat.__init__(self, bpp)
        if bpp == 1:
            self.extension = 'pbm'
        elif bpp == 24:
            self.extension = 'ppm'

    def write_image(self, page_job, render_layers, file):
        size = page_job.size
        rect = (0, 0) + size
        if self._pixel_format.bpp == 1:
            file.write('P4 {0} {1}\n'.format(*size))  # PBM header
        else:
            file.write('P6 {0} {1} 255\n'.format(*size))  # PPM header
        data = page_job.render(
            render_layers,
            rect, rect,
            self._pixel_format
        )
        file.write(data)

class BMP(ImageFormat):

    '''
    Uncompressed Windows Bitmap.

    https://www.fileformat.info/format/bmp/egff.htm
    '''

    extension = 'bmp'

    _rgb = 'BGR'

    def __init__(self, bpp):
        ImageFormat.__init__(self, bpp)
        self._pixel_format.rows_top_to_bottom = 0

    def write_image(self, page_job, render_layers, file):
        size = page_job.size
        rect = (0, 0) + size
        dpm = int(page_job.dpi * 39.37 + 0.5)
        data = page_job.render(
            render_layers,
            rect, rect,
            self._pixel_format,
            row_alignment=4,
        )
        n_palette_colors = 2 * (self._pixel_format.bpp == 1)
        headers_size = 54 + 4 * n_palette_colors
        file.write(struct.pack('<ccIHHI',
            'B', 'M',  # magic
            len(data) + headers_size,  # whole file size
            0, 0,  # identification magic
            headers_size  # offset to pixel data
        ))
        file.write(struct.pack('<IIIHHIIIIII',
            40,  # size of this header
            size[0], size[1],  # image size in pixels
            1,  # number of color planes
            self._pixel_format.bpp,  # number of bits per pixel
            0,  # compression method
            len(data),  # size of pixel data
            dpm, dpm,  # resolution in pixels/meter
            n_palette_colors,  # number of colors in the color palette
            n_palette_colors  # number of important colors
        ))
        if self._pixel_format.bpp == 1:
            # palette:
            file.write(struct.pack('<BBBB', 0xFF, 0xFF, 0xFF, 0))
            file.write(struct.pack('<BBBB', 0, 0, 0, 0))
        file.write(data)

class TIFF(ImageFormat):

    '''
    Uncompressed TIFF.

    https://www.fileformat.info/format/tiff/corion.htm
    '''

    extension = 'tif'
    # Ideally it should be 'tiff',
    # but Tesseract is not happy with such an extension

    def write_image(self, page_job, render_layers, file):
        size = page_job.size
        rect = (0, 0) + size
        data = page_job.render(
            render_layers,
            rect, rect,
            self._pixel_format
        )
        if self._pixel_format.bpp == 1:
            interp = 0
            spp = 1
        elif self._pixel_format.bpp == 24:
            interp = 2
            spp = 3
        else:
            raise NotImplementedError('Cannot output {0}-bpp images'.format(self._pixel_format.bpp))
        n_tags = 9
        data_offset = 28 + n_tags * 12
        header = []
        header += struct.pack('<ccHI', 'I', 'I', 42, 22),  # main header
        header += struct.pack('<HHH', 8, 8, 8),  # bits per sample
        header += struct.pack('<II', page_job.dpi, 1),  # resolution
        header += struct.pack('<H', n_tags),  # number of tags
        header += struct.pack('<HHII', 0x100, 4, 1, size[0]),  # ImageWidth
        header += struct.pack('<HHII', 0x101, 4, 1, size[1]),  # ImageLength
        if interp > 0:
            header += struct.pack('<HHII', 0x102, 3, 3, 8),  # BitsPerSample
        else:
            header += struct.pack('<HHII', 0x102, 3, 1, 1),  # BitsPerSample
        header += struct.pack('<HHIHxx', 0x106, 3, 1, interp),  # PhotometricInterpretation
        header += struct.pack('<HHII', 0x111, 4, 1, data_offset),  # StripOffsets
        header += struct.pack('<HHIHxx', 0x115, 3, 1, spp),  # SamplesPerPixel
        header += struct.pack('<HHII', 0x117, 4, 1, len(data)),  # StripByteCounts
        header += struct.pack('<HHII', 0x11A, 5, 1, 14),  # XResolution
        header += struct.pack('<HHII', 0x11B, 5, 1, 14),  # YResolution
        header += struct.pack('<I', 0),  # offset to next IFD
        assert len(header) == n_tags + 5
        header = ''.join(header)
        assert len(header) == data_offset
        file.write(header)
        file.write(data)

# vim:ts=4 sts=4 sw=4 et
