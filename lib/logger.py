#!/usr/bin/python
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

import logging

logger = None

def setup():
    global logger
    logger = logging.getLogger('ocrodjvu.main')
    ipc_logger = logging.getLogger('ocrodjvu.ipc')
    # Main handler:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    # IPC handler:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('+ %(message)s')
    handler.setFormatter(formatter)
    ipc_logger.addHandler(handler)
    ipc_logger.setLevel(logging.INFO)
    return logger

__all__ = ['setup']

# vim:ts=4 sw=4 et
