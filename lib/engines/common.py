# encoding=UTF-8

# Copyright © 2010 Jakub Wilk <jwilk@jwilk.net>
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

class Engine(object):

    name = None
    input_format = None
    output_format = None

    def __init__(self, *args, **kwargs):
        assert args == ()
        assert isinstance(self.name, str)
        # We do not check self.{input,output}_format here.
        # Values for these attributes might be not available at this point.
        for key, value in kwargs.iteritems():
            try:
                prop = getattr(type(self), key)
                if not isinstance(prop, utils.property):
                    raise AttributeError
            except AttributeError, ex:
                ex.args = ('%r is not a valid property for the %s engine' % (key, self.name),)
                raise
            setattr(self, key, value)

# vim:ts=4 sw=4 et
