# encoding=UTF-8

# Copyright © 2011-2018 Jakub Wilk <jwilk@jwilk.net>
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

import logging

def setup():
    logger = logging.getLogger('ocrodjvu.main')
    ipc_logger = logging.getLogger('ocrodjvu.ipc')
    # Main handler:
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    # IPC handler:
    if not ipc_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('+ %(message)s')
        handler.setFormatter(formatter)
        ipc_logger.addHandler(handler)
        ipc_logger.setLevel(logging.INFO)
    return logger

__all__ = ['setup']

# vim:ts=4 sts=4 sw=4 et
