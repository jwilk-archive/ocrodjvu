#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008, 2009 Jakub Wilk <ubanus@users.sf.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

from __future__ import with_statement

import argparse
import contextlib
import inspect
import os.path
import re
import shutil
import sys
import tempfile

import djvu.decode

from . import errors
from . import hocr
from . import ipc
from . import tesseract
from . import version

__version__ = version.__version__

PIXEL_FORMAT = djvu.decode.PixelFormatPackedBits('>')
PIXEL_FORMAT.rows_top_to_bottom = 1
PIXEL_FORMAT.y_top_to_bottom = 1

class Saver(object):

    in_place = False

    def save(self, document, pages, djvu_path, sed_file):
        raise NotImplementedError

class BundledSaver(Saver):

    '''save results as a bundled multi page-document'''

    options = '-o', '--save-bundled'

    def __init__(self, save_path):
        self._save_path = os.path.abspath(save_path)

    def save(self, document, pages, djvu_path, sed_file):
        file = open(self._save_path, 'wb')
        try:
            document.save(file=file, pages=pages)
        finally:
            file.close()
        InPlaceSaver().save(None, pages, self._save_path, sed_file)

class IndirectSaver(Saver):

    '''save results as an indirect multi page-document'''

    options = '-i', '--save-indirect'

    def __init__(self, save_path):
        self._save_path = os.path.abspath(save_path)

    def save(self, document, pages, djvu_path, sed_file):
        document.save(indirect=self._save_path, pages=pages)
        InPlaceSaver().save(None, pages, self._save_path, sed_file)

class ScriptSaver(Saver):

    '''save a djvused script with results'''

    options = '--save-script',

    def __init__(self, save_path):
        self._save_path = os.path.abspath(save_path)

    def save(self, document, pages, djvu_path, sed_file):
        shutil.copyfile(sed_file.name, self._save_path)

class InPlaceSaver(Saver):

    '''save results in-place'''

    options = '--in-place',
    in_place = True

    def save(self, document, pages, djvu_path, sed_file):
        djvused = ipc.Subprocess([
            'djvused', '-s', '-f',
            os.path.abspath(sed_file.name),
            os.path.abspath(djvu_path)
        ])
        djvused.wait()

class DryRunSaver(Saver):

    '''don't change any files'''

    options = '--dry-run',

    def save(self, document, pages, djvu_path, sed_file):
        pass

class OcrEngine(object):

    pass

class Ocropus(OcrEngine):

    name = 'ocropus'
    has_charboxes = False
    script_name = None

    def __init__(self):
        # Determine:
        # - if OCRopus is installed and
        # - which version we are dealing with
        for script_name in 'recognize', 'rec_test':
            try:
                ocropus = ipc.Subprocess(['ocroscript', script_name],
                    stdout=ipc.PIPE,
                    env=dict(LC_ALL='C', LANG='C')
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
            self.script_name = script_name
            break
        else:
            raise errors.EngineNotFound(self.name)
        if script_name == 'recognize':
            # OCRopus ≥ 0.3
            self.has_charboxes = True

    @staticmethod
    def get_default_language():
        return os.getenv('tesslanguage') or 'eng'

    @staticmethod
    def has_language(language):
        return tesseract.has_language(language)

    @staticmethod
    def list_languages():
        for language in tesseract.get_languages():
            yield language

    @contextlib.contextmanager
    def recognize(self, pbm_file, language, details=hocr.TEXT_DETAILS_WORD):
        def get_command_line():
            yield 'ocroscript'
            yield self.script_name
            if self.has_charboxes and details < hocr.TEXT_DETAILS_LINE:
                yield '--charboxes'
            yield pbm_file.name
        ocropus = ipc.Subprocess(list(get_command_line()),
            stdout=ipc.PIPE,
            env=dict(tesslanguage=language)
        )
        try:
            yield ocropus.stdout
        finally:
            ocropus.wait()

class ArgumentParser(argparse.ArgumentParser):

    savers = BundledSaver, IndirectSaver, ScriptSaver, InPlaceSaver, DryRunSaver
    engines = Ocropus,
    default_engine = Ocropus

    _details_map = dict(
        lines=hocr.TEXT_DETAILS_LINE,
        words=hocr.TEXT_DETAILS_WORD,
        chars=hocr.TEXT_DETAILS_CHARACTER,
    )

    def __init__(self):
        usage = '%(prog)s [options] FILE'
        version = '%(prog) ' + __version__
        argparse.ArgumentParser.__init__(self, usage=usage, version=version)
        saver_group = self.add_argument_group(title='arguments controlling output')
        for saver_type in self.savers:
            options = saver_type.options
            try:
                init_args, _, _, _ = inspect.getargspec(saver_type.__init__)
                n_args = len(init_args) - 1
            except TypeError:
                n_args = 0
            metavar = None
            if n_args == 1:
                metavar = 'FILE'
            saver_group.add_argument(
                *options,
                **dict(
                    metavar=metavar,
                    action=self.set_output,
                    saver_type=saver_type, nargs=n_args,
                    help=saver_type.__doc__
                )
            )
        self.add_argument('--engine', dest='engine', nargs=1, action=self.set_engine, default=self.default_engine, help=argparse.SUPPRESS or 'set OCR engine')
        self.add_argument('--list-engines', action=self.list_engines, nargs=0, help=argparse.SUPPRESS or 'print list of available OCR engines')
        self.add_argument('--ocr-only', dest='ocr_only', action='store_true', default=False, help='''don't save pages without OCR''')
        self.add_argument('--clear-text', dest='clear_text', action='store_true', default=False, help='remove existing hidden text')
        self.add_argument('--language', dest='language', help='set recognition language')
        self.add_argument('--list-languages', action=self.list_languages, nargs=0, help='print list of available languages')
        self.add_argument('-p', '--pages', dest='pages', action='store', default=None, help='pages to process')
        self.add_argument('-D', '--debug', dest='debug', action='store_true', default=False, help='''don't delete intermediate files''')
        self.add_argument('path', metavar='FILE', help='DjVu file to process')
        group = self.add_argument_group(title='text segmentation options')
        group.add_argument('-t', '--details', dest='details', choices=('lines', 'words', 'chars'), action='store', default='words', help='amount of text details to extract')
        group.add_argument('--word-segmentation', dest='word_segmentation', choices=('simple', 'uax29'), default='space', help='word segmentation algorithm')

    class set_engine(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            [value] = values
            for engine in parser.engines:
                if engine.name != value:
                    continue
                namespace.engine = engine
                break
            else:
                parser.error('Invalid OCR engine name')

    class list_engines(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            for engine in parser.engines:
                try:
                    engine = engine()
                except errors.EngineNotFound:
                    pass
                else:
                    print engine.name
            sys.exit(0)

    class list_languages(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            try:
                for language in namespace.engine().list_languages():
                    print language
            except errors.EngineNotFound, ex:
                print >>sys.stderr, ex
                sys.exit(1)
            except errors.UnknownLanguageList:
                print >>sys.stderr, ex
                sys.exit(1)
            else:
                sys.exit(0)

    class set_output(argparse.Action):
        def __init__(self, **kwargs):
            self.saver_type = kwargs.pop('saver_type')
            argparse.Action.__init__(self, **kwargs)
        def __call__(self, parser, namespace, values, option_string=None):
            try:
                namespace.saver
            except AttributeError:
                namespace.saver = self.saver_type(*values)
            else:
                namespace.saver = None

    def parse_args(self):
        options = argparse.ArgumentParser.parse_args(self)
        try:
            if options.pages is not None:
                pages = []
                for range in options.pages.split(','):
                    if '-' in range:
                        x, y = map(int, options.pages.split('-', 1))
                        pages += xrange(x, y + 1)
                    else:
                        pages += int(range),
                options.pages = pages
        except (TypeError, ValueError):
            self.error('Unable to parse page numbers')
        options.details = self._details_map[options.details]
        try:
            saver = options.saver
        except AttributeError:
            saver = None
        if saver is None:
            self.error(
                'You must use exactly one of the following options: %s' %
                ', '.join('/'.join(saver.options) for saver in self.savers)
            )
        # It might be temping to verify language name correctness at argument
        # parse time (rather than after argument parsing). However, it's
        # desirable to be able to specify a language *before* specifying an OCR
        # engine.
        if options.language is None:
            options.language = options.engine.get_default_language()
        try:
            if not options.engine.has_language(options.language):
                self.error('Language pack for the selected language (%s) is not available.' % options.language)
        except errors.InvalidLanguageId, ex:
            self.error(str(ex))
        except errors.UnknownLanguageList:
            # For now, let's assume the language pack is installed
            pass
        options.uax29 = options.language if options.word_segmentation == 'uax29' else None
        return options

def validate_file_id(id):
    if re.compile(r'[/\\\s]').search(id):
        raise errors.SecurityConcern()
    return id


class Context(djvu.decode.Context):

    def init(self, options):
        self._temp_dir = tempfile.mkdtemp(prefix='ocrodjvu.')
        self._debug = options.debug
        self._options = options

    def _temp_file(self, name):
        path = os.path.join(self._temp_dir, name)
        file = open(path, 'w+b')
        if not self._debug:
            file = tempfile._TemporaryFileWrapper(file, file.name)
        return file

    def handle_message(self, message):
        if isinstance(message, djvu.decode.ErrorMessage):
            print >>sys.stderr, message
            sys.exit(1)

    def process_page(self, page):
        print >>sys.stderr, '- Page #%d' % (page.n + 1)
        page_job = page.decode(wait=True)
        size = page_job.size
        rect = (0, 0) + size
        pfile = self._temp_file('%06d.pbm' % page.n)
        try:
            pfile.write('P4 %d %d\n' % size) # PBM header
            data = page_job.render(
                djvu.decode.RENDER_MASK_ONLY,
                rect, rect,
                PIXEL_FORMAT
            )
            pfile.write(data)
            pfile.flush()
            html_file = None
            with self._engine.recognize(pfile, language=self._options.language, details=self._options.details) as result:
                try:
                    if self._debug:
                        html_file = self._temp_file('%06d.html' % page.n)
                        html = result.read()
                        html_file.write(html)
                        html_file.seek(0)
                    else:
                        html_file = result
                    text, = hocr.extract_text(html_file,
                        rotation=page.rotation,
                        details=self._options.details,
                        uax29=self._options.uax29
                    )
                    return text
                finally:
                    if html_file is not None:
                        html_file.close()
        finally:
            pfile.close()

    def process(self, path, pages=None):
        try:
            self._engine = self._options.engine()
        except errors.EngineNotFound, ex:
            print >>sys.stderr, ex
            sys.exit(1)
        print >>sys.stderr, 'Processing %r:' % path
        document = self.new_document(djvu.decode.FileURI(path))
        document.decoding_job.wait()
        if pages is None:
            pages = list(document.pages)
        else:
            pages = [document.pages[i - 1] for i in pages]
        sed_file = self._temp_file('ocrodjvu.djvused')
        try:
            if self._options.clear_text:
                sed_file.write('remove-txt\n')
            for page in pages:
                sed_file.write('select %s\n' % validate_file_id(page.file.id))
                sed_file.write('set-txt\n')
                try:
                    self.process_page(page).print_into(sed_file)
                except djvu.decode.NotAvailable:
                    print >>sys.stderr, 'No image suitable for OCR.'
                sed_file.write('\n.\n\n')
            sed_file.flush()
            saver = self._options.saver
            if saver.in_place:
                document = None
            pages_to_save = None
            if self._options.ocr_only:
                pages_to_save = [page.n for page in pages]
            self._options.saver.save(document, pages_to_save, path, sed_file)
            document = None
        finally:
            sed_file.close()

    def close(self):
        if self._debug:
            return self._temp_dir
        else:
            shutil.rmtree(self._temp_dir)

def main():
    options = ArgumentParser().parse_args()
    context = Context()
    context.init(options)
    try:
        context.process(options.path, options.pages)
    finally:
        temp_dir = context.close()
        if temp_dir is not None:
            print >>sys.stderr, 'Intermediate files were left in the %r directory.' % temp_dir

# vim:ts=4 sw=4 et
