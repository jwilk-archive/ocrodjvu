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

__version__ = '0.2.2'

import inspect
import optparse
import os.path
import re
import shutil
import sys
import tempfile

import djvu.decode

import hocr
import ipc
import tesseract

PIXEL_FORMAT = djvu.decode.PixelFormatPackedBits('>')
PIXEL_FORMAT.rows_top_to_bottom = 1
PIXEL_FORMAT.y_top_to_bottom = 1


class SecurityConcern(Exception):

    def __init__(self):
        Exception.__init__(self, 'I refuse to process this file due to security concerns')

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

class OptionParser(optparse.OptionParser):

    savers = BundledSaver, IndirectSaver, ScriptSaver, InPlaceSaver, DryRunSaver

    def __init__(self):
        usage = '%prog [options] <djvu-file>'
        version = '%%prog %s' % __version__
        optparse.OptionParser.__init__(self, usage=usage, version=version)
        for saver_type in self.savers:
            options = saver_type.options
            try:
                init_args, _, _, _ = inspect.getargspec(saver_type.__init__)
                n_args = len(init_args) - 1
            except TypeError:
                n_args = 0
            arg_type = None
            metavar = None
            if n_args > 0:
                arg_type = 'string'
            if n_args == 1:
                metavar = 'FILE'
            self.add_option(
                *options,
                **dict(
                    type=arg_type, metavar=metavar,
                    action='callback', callback=self.set_output,
                    callback_args=(saver_type,), nargs=n_args,
                    help=saver_type.__doc__
                )
            )
        self.add_option('--ocr-only', dest='ocr_only', action='store_true', default=False, help='''don't save pages without OCR''')
        self.add_option('--clear-text', dest='clear_text', action='store_true', default=False, help='remove exisiting hidden text')
        self.add_option('--language', dest='language', help='set recognition language')
        self.add_option('--list-languages', action='callback', callback=self.list_languages, help='print list of supported languages')
        self.add_option('-p', '--pages', dest='pages', action='store', default=None, help='pages to convert')
        self.add_option('-D', '--debug', dest='debug', action='store_true', default=False, help='''don't delete intermediate files''')

    @staticmethod
    def list_languages(option, opt_str, value, parser):
        try:
            for language in tesseract.get_languages():
                print language
        except tesseract.UnknownLanguageList:
            print >>sys.stderr, 'Unable to determine list of supported languages'
            sys.exit(1)
        sys.exit(0)

    @staticmethod
    def set_output(option, opt_str, value, parser, *args):
        [saver_type] = args
        try:
            parser.values.saver
        except AttributeError:
            if value is None:
                value = []
            else:
                value = [value]
            parser.values.saver = saver_type(*value)
        else:
            parser.values.saver = None

    def parse_args(self):
        try:
            options, [path] = optparse.OptionParser.parse_args(self)
        except ValueError:
            self.error('Invalid number of arguments')
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
        try:
            saver = options.saver
        except AttributeError:
            saver = None
        if saver is None:
            self.error(
                'You must use exactly one of the following options: %s' %
                ', '.join('/'.join(saver.options) for saver in self.savers)
            )
        return options, path

def validate_file_id(id):
    if re.compile(r'[/\\\s]').search(id):
        raise SecurityConcern()
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
            ocropus = ipc.Subprocess(['ocroscript', 'rec-tess', pfile.name], stdout=ipc.PIPE)
            html_file = None
            try:
                if self._debug:
                    html_file = self._temp_file('%06d.html' % page.n)
                    html = ocropus.stdout.read()
                    html_file.write(html)
                    html_file.seek(0)
                else:
                    html_file = ocropus.stdout
                text, = hocr.extract_text(html_file, page.rotation)
                return text
            finally:
                if html_file is not None:
                    html_file.close()
                ocropus.wait()
        finally:
            pfile.close()

    def process(self, path, pages=None):
        print >>sys.stderr, 'Processing %r:' % path
        if self._options.language is not None:
            os.putenv('tesslanguage', self._options.language)
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
    oparser = OptionParser()
    options, path = oparser.parse_args()
    context = Context()
    context.init(options)
    try:
        context.process(path, options.pages)
    finally:
        temp_dir = context.close()
        if temp_dir is not None:
            print >>sys.stderr, 'Intermediate files were left in the %r directory.' % temp_dir

# vim:ts=4 sw=4 et
