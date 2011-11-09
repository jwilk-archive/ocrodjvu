# encoding=UTF-8

# Copyright © 2011 Jakub Wilk <jwilk@jwilk.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

from . import utils

def parse(stream):
    try:
        import html5lib
    except ImportError, ex:
        utils.enhance_import_error(ex, 'html5lib', 'python-html5lib', 'http://code.google.com/p/html5lib/')
        raise
    return html5lib.parse(stream,
        treebuilder='lxml',
        namespaceHTMLElements=False
    )

# vim:ts=4 sw=4 et
