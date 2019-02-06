# encoding=UTF-8

# Copyright © 2010-2019 Jakub Wilk <jwilk@jwilk.net>
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

from .. import utils
from .. import image_io

import io

class Engine(object):

    name = None
    image_format = None
    needs_utf8_fix = False
    default_language = 'eng'

    def __init__(self, *args, **kwargs):
        tpname = '{mod}.{tp}'.format(tp=type(self).__name__, mod=self.__module__)
        if args:
            raise ValueError('{tp}.__init__() takes no positional arguments'.format(tp=tpname))  # no coverage
        if not isinstance(self.name, str):
            raise TypeError('{tp}.name must be a string'.format(tp=tpname))  # no coverage
        if not issubclass(self.image_format, image_io.ImageFormat):
            raise TypeError('{tp}.image_format must be an ImageFormat subclass'.format(tp=tpname))  # no coverage
        for key, value in kwargs.iteritems():
            try:
                prop = getattr(type(self), key)
                if not isinstance(prop, utils.property):
                    raise AttributeError
            except AttributeError as ex:
                ex.args = ('{key!r} is not a valid property for the {engine} engine'.format(key=key, engine=self.name),)
                raise
            setattr(self, key, value)

class Output(object):

    format = None

    def __init__(self, contents, format=None):
        self._contents = contents
        if format is not None:
            self.format = format
        if self.format is None:
            raise TypeError('output format is not defined')

    def __str__(self):
        return self._contents

    def save(self, prefix):
        path = '{base}.{ext}'.format(base=prefix, ext=self.format)
        with open(path, 'wb') as file:
            file.write(str(self))

    def as_stringio(self):
        return io.BytesIO(str(self))

# vim:ts=4 sts=4 sw=4 et
