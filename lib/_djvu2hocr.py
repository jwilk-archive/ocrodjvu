# encoding=UTF-8
# Copyright © 2009 Jakub Wilk <ubanus@users.sf.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

import argparse
import os
import sys

from . import hocr
from . import ipc
from . import utils
from . import version

from .hocr import ET
from .hocr import sexpr
from .hocr import const

__version__ = version.__version__

class ArgumentParser(argparse.ArgumentParser):

    def __init__(self):
        usage = '%(prog)s [options] FILE'
        version = '%(prog) ' + __version__
        argparse.ArgumentParser.__init__(self, usage=usage, version=version)
        self.add_argument('-p', '--pages', dest='pages', action='store', default=None, help='pages to convert')
        self.add_argument('path', metavar='FILE', help='DjVu file to process')

    def parse_args(self):
        options = argparse.ArgumentParser.parse_args(self)
        try:
            options.pages = utils.parse_page_numbers(options.pages)
        except (TypeError, ValueError):
            self.error('Unable to parse page numbers')
        return options

def process_zone(parent, parent_zone_type, page_text):
    zone_type = const.get_text_zone_type(page_text[0].value)
    if zone_type <= const.TEXT_ZONE_LINE and parent is not None:
        parent.tail = '\n'
    hocr_tag, hocr_class = hocr.djvu_zone_to_hocr(zone_type)
    self = ET.Element(hocr_tag)
    self.set('class', hocr_class)
    self.set('title', 'bbox ' + ' '.join(
        str(page_text[i].value)
        for i in xrange(1, 5)
    ))
    child = None
    for child in page_text[5:]:
        if isinstance(child, sexpr.ListExpression):
            process_zone(self, zone_type, child)
        else:
            self.text = unicode(child.value, 'UTF-8', 'replace')
            if zone_type == const.TEXT_ZONE_WORD:
                self.tail = ' '
    if parent is not None:
        parent.append(self)
    return self

def process_page(page_text):
    result = process_zone(None, None, page_text)
    tree = ET.ElementTree(result)
    tree.write(sys.stdout, encoding='UTF-8')

hocr_header = '''\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <title>DjVu hidden text layer</title>
</head>
<body>
'''

hocr_footer = '''
</body>
</html>
'''

def main():
    options = ArgumentParser().parse_args()
    if options.pages is None:
        sed_script = 'print-txt'
    else:
        sed_script = ''.join('select %d; print-txt; ' % n for n in options.pages)
    djvused = ipc.Subprocess([
        'djvused', '-e', sed_script,
        os.path.abspath(options.path),
    ], stdout=ipc.PIPE)
    sys.stdout.write(hocr_header)
    while 1:
        try:
            page_text = sexpr.Expression.from_stream(djvused.stdout)
        except sexpr.ExpressionSyntaxError:
            break
        process_page(page_text)
    sys.stdout.write(hocr_footer)
    djvused.wait()

# vim:ts=4 sw=4 et
