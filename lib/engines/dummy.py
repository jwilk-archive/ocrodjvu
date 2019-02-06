# encoding=UTF-8

# Copyright © 2018-2019 Jakub Wilk <jwilk@jwilk.net>
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

from . import common
from .. import image_io
from .. import text_zones

class Engine(common.Engine):

    name = '_dummy'
    image_format = image_io.PNM

    def check_language(self, language):
        return

    def list_languages(self):
        return []

    def recognize(self, image, language, details=None, uax29=None):
        return common.Output('', format='dummy')

    def extract_text(self, stream, **kwargs):
        bbox = text_zones.BBox(0, 0, 0, 0)
        page = text_zones.Zone(text_zones.const.TEXT_ZONE_PAGE, bbox, [])
        return [page.sexpr]

# vim:ts=4 sts=4 sw=4 et
