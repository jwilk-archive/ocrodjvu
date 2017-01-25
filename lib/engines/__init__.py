# encoding=UTF-8

# Copyright © 2010-2015 Jakub Wilk <jwilk@jwilk.net>
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

import pkgutil

def get_engines():
    for importer, name, ispkg in pkgutil.iter_modules(__path__):
        thismodule = __import__('', globals=globals(), fromlist=(name,), level=1)
        engine = getattr(thismodule, name).Engine
        if engine.name is None:
            continue
        yield engine

# vim:ts=4 sts=4 sw=4 et
