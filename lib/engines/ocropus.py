# encoding=UTF-8
# Copyright © 2008, 2009, 2010 Jakub Wilk <jwilk@jwilk.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

import contextlib
import os

from . import tesseract
from .. import errors
from .. import hocr
from .. import ipc

class Engine(object):

    name = 'ocropus'
    image_format = 'ppm'
    output_format = 'html'
    has_charboxes = False
    script_name = None

    def __init__(self):
        # Determine:
        # - if OCRopus is installed and
        # - which version we are dealing with
        for script_name in 'recognize', 'rec-tess':
            try:
                ocropus = ipc.Subprocess(['ocroscript', script_name],
                    stdout=ipc.PIPE,
                    stderr=ipc.PIPE,
                )
            except OSError:
                raise errors.EngineNotFound(name)
            try:
                found = ocropus.stdout.read(7) == 'Usage: '
            finally:
                try:
                    ocropus.wait()
                except ipc.CalledProcessError:
                    pass
            if found:
                self.script_name = script_name
                break
        else:
            raise errors.EngineNotFound(name)
        if script_name == 'recognize':
            # OCRopus ≥ 0.3
            self.has_charboxes = True

    get_default_language = staticmethod(tesseract.get_default_language)
    has_language = staticmethod(tesseract.has_language)
    list_languages = staticmethod(tesseract.get_languages)

    @contextlib.contextmanager
    def recognize(self, pbm_file, language, details=hocr.TEXT_DETAILS_WORD):
        def get_command_line():
            yield 'ocroscript'
            assert self.script_name is not None
            yield self.script_name
            if self.has_charboxes and details < hocr.TEXT_DETAILS_LINE:
                yield '--charboxes'
            yield pbm_file.name
        ocropus = ipc.Subprocess(list(get_command_line()),
            stdout=ipc.PIPE,
            env=dict(tesslanguage=language),
        )
        try:
            yield ocropus.stdout
        finally:
            ocropus.wait()

    extract_text = staticmethod(hocr.extract_text)

# vim:ts=4 sw=4 et
