# encoding=UTF-8

# Copyright © 2008-2019 Jakub Wilk <jwilk@jwilk.net>
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

import shlex

from . import common
from . import tesseract
from .. import errors
from .. import image_io
from .. import ipc
from .. import utils

class Engine(common.Engine):

    name = 'ocropus'
    image_format = image_io.PNM

    executable = utils.property('ocroscript')
    tesseract_executable = utils.property('tesseract')
    extra_args = utils.property([], shlex.split)
    script_name = utils.property()
    has_charboxes = utils.property()

    def __init__(self, *args, **kwargs):
        common.Engine.__init__(self, **kwargs)
        self.tesseract = tesseract.Engine(executable=self.tesseract_executable)
        # Determine:
        # - if OCRopus is installed and
        # - which version we are dealing with
        if self.script_name is None:
            script_names = ['recognize', 'rec-tess']
        else:
            script_names = [self._script_name]
        for script_name in script_names:
            try:
                ocropus = ipc.Subprocess(['ocroscript', script_name],
                    stdout=ipc.PIPE,
                    stderr=ipc.PIPE,
                )
            except OSError:
                raise errors.EngineNotFound(self.name)
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
            raise errors.EngineNotFound(self.name)
        if self.has_charboxes is None and script_name == 'recognize':
            # OCRopus ≥ 0.3
            self.has_charboxes = True
        # Import hocr late,
        # so that lxml is imported only when needed.
        from .. import hocr
        self._hocr = hocr

    def check_language(self, language):
        return self.tesseract.check_language(language)

    def list_languages(self):
        return self.tesseract.list_languages()

    def recognize(self, image, language, details=None, uax29=None):
        hocr = self._hocr
        if details is None:
            details = hocr.TEXT_DETAILS_WORD
        def get_command_line():
            yield self.executable
            assert self.script_name is not None
            yield self.script_name
            if self.has_charboxes and details < hocr.TEXT_DETAILS_LINE:
                yield '--charboxes'
            for arg in self.extra_args:
                yield arg
            yield image.name
        ocropus = ipc.Subprocess(list(get_command_line()),
            stdout=ipc.PIPE,
            env=dict(tesslanguage=language),
        )
        try:
            return common.Output(
                ocropus.stdout.read(),
                format='html',
            )
        finally:
            ocropus.wait()

    def extract_text(self, *args, **kwargs):
        return self._hocr.extract_text(*args, **kwargs)

# vim:ts=4 sts=4 sw=4 et
