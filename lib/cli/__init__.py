# encoding=UTF-8

# Copyright © 2011-2015 Jakub Wilk <jwilk@jwilk.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

from .. import utils

try:
    import argparse
except ImportError as ex:  # no coverage
    utils.enhance_import_error(ex, 'argparse', 'python-argparse', 'https://pypi.python.org/pypi/argparse')
    raise

argparse.ArgumentParser  # quieten pyflakes

# vim:ts=4 sts=4 sw=4 et
