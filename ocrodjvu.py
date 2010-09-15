# encoding=UTF-8
# Copyright © 2010 Jakub Wilk <jwilk@jwilk.net>
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
Helper module that allows to use command-line tools without installing them.
'''

class cli(object):

    @classmethod
    def main(cls, *args, **kwargs):
        name = cls.__name__
        module = __import__('lib', fromlist=[name])
        module = getattr(module, name)
        return module.main(*args, **kwargs)

class _ocrodjvu(cli):
    pass

class _hocr2djvused(cli):
    pass

class _djvu2hocr(cli):
    pass

del cli

# vim:ts=4 sw=4 et
