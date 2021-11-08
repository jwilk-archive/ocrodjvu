# encoding=UTF-8

# Copyright © 2015 Jakub Wilk <jwilk@jwilk.net>
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

from __future__ import unicode_literals
import io
import distutils.version

from tests.tools import (
    assert_equal,
)

from lib import text_zones

V = distutils.version.LooseVersion
python_djvulibre_version = V(text_zones.decode.__version__)

def test_print_sexpr():
    inp = 'jeż'
    if python_djvulibre_version < V('0.4'):
        out = r'"je\305\274"'
    else:
        out = u'"jeż"'
    fp = io.StringIO()
    expr = text_zones.sexpr.Expression(inp)
    text_zones.print_sexpr(expr, fp)
    fp.seek(0)
    assert_equal(fp.getvalue(), out)

# vim:ts=4 sts=4 sw=4 et
