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

import pkgutil

def get_engines():
    for importer, name, ispkg in pkgutil.iter_modules(__path__):
        thismodule = __import__('', globals=globals(), fromlist=(name,), level=1)
        try:
            engine = getattr(thismodule, name).Engine
            if engine.name is None:
                continue
        except AttributeError:
            continue
        else:
            yield engine

# vim:ts=4 sw=4 et
