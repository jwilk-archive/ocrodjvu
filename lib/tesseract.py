#!/usr/bin/python
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

import glob
import os
import re

import ipc

class UnknownLanguageList(Exception):
    pass

_pattern = re.compile(r"^Unable to load unicharset file (/.*)/[.]unicharset\n$", re.DOTALL)

def get_languages():
    try:
        tesseract = ipc.Subprocess(['tesseract', '', '', '-l', ''],
            stdout=ipc.PIPE,
            stderr=ipc.PIPE,
            env=dict(LC_ALL='C')
        )
    except OSError:
        raise UnknownLanguageList
    try:
        line = tesseract.stderr.read()
        match = _pattern.match(line)
        if match is None:
            raise UnknownLanguageList
        directory = match.group(1)
        if not os.path.isdir(directory):
            raise UnknownLanguageList
    finally:
        try:
            tesseract.wait()
        except ipc.CalledProcessError, ex:
            pass
        else:
            raise UnknownLanguageList
    for filename in glob.glob(os.path.join(directory, '*.unicharset')):
        filename = os.path.basename(filename)
        language = os.path.splitext(filename)[0]
        yield language

# vim:ts=4 sw=4 et
