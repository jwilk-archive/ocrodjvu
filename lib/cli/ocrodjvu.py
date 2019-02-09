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

from __future__ import print_function

import argparse
import contextlib
import inspect
import locale
import os.path
import shutil
import string
import sys
import threading
import traceback

from .. import cli
from .. import engines
from .. import errors
from .. import ipc
from .. import logger
from .. import temporary
from .. import text_zones
from .. import utils
from .. import version

# Import this after local modules, so that they can take care of a showing
# a nice ImportError message.
import djvu.decode

__version__ = version.__version__

system_encoding = locale.getpreferredencoding()

logger = logger.setup()

class Saver(object):

    in_place = False

    def check(self):
        pass

    @utils.not_overridden
    def save(self, document, pages, djvu_path, sed_file):
        raise NotImplementedError('Cannot save results in this format')  # no coverage

class BundledSaver(Saver):

    '''save results as a bundled multi-page document'''

    options = '-o', '--save-bundled'

    def __init__(self, save_path):
        self._ips = InPlaceSaver()
        self._save_path = os.path.abspath(save_path)

    def check(self):
        self._ips.check()

    def save(self, document, pages, djvu_path, sed_file):
        file = open(self._save_path, 'wb')
        try:
            document.save(file=file, pages=pages)
        finally:
            file.close()
        self._ips.save(None, pages, self._save_path, sed_file)

class IndirectSaver(Saver):

    '''save results as an indirect multi-page document'''

    options = '-i', '--save-indirect'

    def __init__(self, save_path):
        self._ips = InPlaceSaver()
        self._save_path = os.path.abspath(save_path)

    def check(self):
        self._ips.check()

    def save(self, document, pages, djvu_path, sed_file):
        document.save(indirect=self._save_path, pages=pages)
        self._ips.save(None, pages, self._save_path, sed_file)

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

    def check(self):
        ipc.require('djvused')

    def save(self, document, pages, djvu_path, sed_file):
        sed_file_name = os.path.abspath(sed_file.name)
        djvu_path = os.path.abspath(djvu_path)
        djvused = ipc.Subprocess(
            ['djvused', '-s', '-f', sed_file_name, djvu_path],
        )
        djvused.wait()

class DryRunSaver(Saver):

    '''don't change any files'''

    options = '--dry-run',

    def save(self, document, pages, djvu_path, sed_file):
        pass

def expand_template(template, pageno, pageid):
    d = {
        'page': pageno,
        'id': pageid,
        'id-ext': os.path.splitext(pageid)[0],
    }
    formatter = string.Formatter()
    for _, var, _, _ in formatter.parse(template):
        if var is None:
            continue
        if '+' in var:
            sign = +1
            base_var, offset = var.split('+')
        elif '-' in var:
            sign = -1
            base_var, offset = var.split('-')
        else:
            continue
        try:
            offset = sign * int(offset, 10)
        except ValueError:
            continue
        try:
            base_value = d[base_var]
        except LookupError:
            continue
        if not isinstance(base_value, int):
            continue
        d[var] = d[base_var] + offset
    return formatter.vformat(template, (), d)

class EngineChoices(object):

    default = 'tesseract'

    def __init__(self):
        self._data = data = {}
        for eng in engines.get_engines():
            data[eng.name] = eng

    def __iter__(self):
        return iter(sorted(
            key
            for key in self._data
            if key[0] != '_'
        ))

    def __contains__(self, key):
        return key in self._data

    def __getitem__(self, key):
        return self._data[key]

class ArgumentParser(cli.ArgumentParser):

    savers = BundledSaver, IndirectSaver, ScriptSaver, InPlaceSaver, DryRunSaver
    engines = EngineChoices()

    _details_map = dict(
        lines=text_zones.TEXT_DETAILS_LINE,
        words=text_zones.TEXT_DETAILS_WORD,
        chars=text_zones.TEXT_DETAILS_CHARACTER,
    )

    _render_map = dict(
        mask=djvu.decode.RENDER_MASK_ONLY,
        foreground=djvu.decode.RENDER_FOREGROUND,
        all=djvu.decode.RENDER_COLOR,
    )

    def __init__(self):
        usage = '%(prog)s [options] FILE'
        cli.ArgumentParser.__init__(self, usage=usage)
        self.add_argument('--version', action=version.VersionAction)
        group = self.add_argument_group(title='options controlling output')
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
            group.add_argument(
                *options,
                **dict(
                    metavar=metavar,
                    action=self.set_output,
                    saver_type=saver_type, nargs=n_args,
                    help=saver_type.__doc__
                )
            )
        group.add_argument('--ocr-only', dest='ocr_only', action='store_true', default=False, help='''don't save pages without OCR''')
        group.add_argument('--clear-text', dest='clear_text', action='store_true', default=False, help='remove existing hidden text')
        group.add_argument('--save-raw-ocr', dest='save_raw_ocr_dir', metavar='DIRECTORY', help='save raw OCR output')
        group.add_argument('--raw-ocr-filename-template', metavar='TEMPLATE', default='{id-ext}', help='file naming scheme for raw OCR')
        self.add_argument('-e', '--engine', dest='engine', choices=self.engines, metavar='ENGINE', help='OCR engine to use (default: {0})'.format(self.engines.default))
        self.add_argument('--list-engines', action=self.list_engines, nargs=0, help='print list of available OCR engines')
        self.add_argument('-l', '--language', dest='language', help='set recognition language')
        self.add_argument('--list-languages', action=self.list_languages, nargs=0, help='print list of available languages')
        self.add_argument('--render', dest='render_layers', choices=self._render_map.keys(), action='store', default='mask', help='image layers to render')
        def pages(x):
            return utils.parse_page_numbers(x)
        self.add_argument('-p', '--pages', dest='pages', action='store', default=None, type=pages, help='pages to process')
        self.add_argument('-j', '--jobs', dest='n_jobs', metavar='N', nargs='?', type=int, default=1, help='number of jobs to run simultaneously')
        self.add_argument('path', metavar='FILE', help='DjVu file to process')
        group = self.add_argument_group(title='text segmentation options')
        group.add_argument('-t', '--details', dest='details', choices=('lines', 'words', 'chars'), action='store', default='words', help='amount of text details to extract')
        group.add_argument('--word-segmentation', dest='word_segmentation', choices=('simple', 'uax29'), default='simple', help='word segmentation algorithm')
        group = self.add_argument_group(title='advanced options')
        group.add_argument('-D', '--debug', dest='debug', action='store_true', default=False, help='''don't delete intermediate files''')
        group.add_argument('-X', dest='properties', metavar='KEY=VALUE', help='set an engine-specific property', action='append', default=[])
        group.add_argument('--on-error', choices=('abort', 'resume'), default='abort', help='error handling strategy')
        group.add_argument('--html5', dest='html5', action='store_true', help='use HTML5 parse')

    class list_engines(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            for ename in parser.engines:
                engine = parser.engines[ename]
                try:
                    engine = engine()
                except errors.EngineNotFound:
                    pass
                else:
                    print(ename)
            sys.exit(0)

    class list_languages(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            ename = namespace.engine or parser.engines.default
            engine = parser.engines[ename]
            try:
                for language in sorted(engine().list_languages()):
                    print(language)
            except errors.EngineNotFound as ex:
                errors.fatal(ex)
            except errors.UnknownLanguageList as ex:
                errors.fatal(ex)
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

    def parse_args(self, args=None, namespace=None):
        options = cli.ArgumentParser.parse_args(self, args, namespace)
        options.details = self._details_map[options.details]
        options.render_layers = self._render_map[options.render_layers]
        options.resume_on_error = options.on_error == 'resume'
        try:
            saver = options.saver
        except AttributeError:
            saver = None
        if saver is None:
            self.error(
                'exactly one of the following options is required: {opt}'.format(
                    opt=', '.join('/'.join(saver.options) for saver in self.savers)
                )
            )
        else:
            try:
                saver.check()
            except OSError as exc:
                errors.fatal('cannot find {path!r}: {msg}'.format(
                    path=exc.filename,
                    msg=exc.strerror,
                ))
        if options.save_raw_ocr_dir is not None:
            try:
                os.stat(os.path.join(options.save_raw_ocr_dir, ''))
            except EnvironmentError as ex:
                errors.fatal('cannot open {path!r}: {msg}'.format(
                    path=ex.filename,
                    msg=ex[1],
                ))
            try:
                expand_template(options.raw_ocr_filename_template, pageno=0, pageid='')
            except ValueError as ex:
                self.error('cannot parse filename template {tmpl!r}: {msg}'.format(
                    tmpl=options.raw_ocr_filename_template,
                    msg=ex,
                ))
            except KeyError as ex:
                self.error('cannot parse filename template {tmpl!r}: unknown field {key!r}'.format(
                    tmpl=options.raw_ocr_filename_template,
                    key=ex.args[0],
                ))
        implicit_default_engine = options.engine is None
        ename = options.engine or self.engines.default
        options.engine = self.engines[ename]
        # It might be tempting to verify language name correctness at argument
        # parse time (rather than after argument parsing). However, it's
        # desirable to be able to specify a language *before* specifying an OCR
        # engine.
        if options.language is None:
            options.language = options.engine.default_language
        kwargs = {}
        for prop in options.properties:
            try:
                key, value = prop.split('=', 1)
            except ValueError:
                self.error('argument -X: expected KEY=VALUE')
            key = key.replace('-', '_')
            kwargs[key] = value
        try:
            options.engine = options.engine(**kwargs)
        except AttributeError as ex:
            errors.fatal(ex)
        except errors.EngineNotFound as ex:
            msg = str(ex)
            if implicit_default_engine:
                msg += '; use -e/--engine to use another engine'
            errors.fatal(msg)
        try:
            options.engine.check_language(options.language)
        except errors.MissingLanguagePack as ex:
            errors.fatal(ex)
        except errors.InvalidLanguageId as ex:
            errors.fatal(ex)
        except errors.UnknownLanguageList:
            # For now, let's assume the language pack is installed.
            pass
        options.uax29 = options.language if options.word_segmentation == 'uax29' else None
        if options.n_jobs is None:
            options.n_jobs = utils.get_cpu_count()
        elif options.n_jobs < 1:
            options.n_jobs = 1
        return options

class Results(dict):
    seen_exception = False

    def __missing__(self, key):
        return

class Context(djvu.decode.Context):

    def init(self, options):
        self._temp_dir = temporary.raw.mkdtemp(prefix='ocrodjvu.')
        self._debug = options.debug
        self._options = options
        bpp = 24 if self._options.render_layers != djvu.decode.RENDER_MASK_ONLY else 1
        self._image_format = self._options.engine.image_format(bpp)

    def _temp_file(self, name, auto_remove=True):
        path = os.path.join(self._temp_dir, name)
        file = open(path, 'w+b')
        if not self._debug and auto_remove:
            file = temporary.wrapper(file, file.name)
        return file

    def handle_message(self, message):
        if isinstance(message, djvu.decode.ErrorMessage):
            logger.warning(message)

    @contextlib.contextmanager
    def get_output_image(self, nth, page_job):
        output_format = self._image_format
        file = self._temp_file('{n:06}.{ext}'.format(
            n=nth,
            ext=output_format.extension
        ))
        try:
            output_format.write_image(page_job, self._options.render_layers, file)
            file.flush()
            yield file
        finally:
            file.close()

    def save_raw_ocr(self, page, result):
        output_dir = self._options.save_raw_ocr_dir
        if output_dir is None:
            return
        template = self._options.raw_ocr_filename_template
        pageid = page.file.id
        pageno = page.n + 1
        prefix = os.path.join(
            output_dir,
            expand_template(template, pageno=pageno, pageid=pageid),
        )
        result.save(prefix)

    def process_page(self, page):
        logger.info('- Page #{0}'.format(page.n + 1))
        page_job = page.decode(wait=True)
        # Because of a bug in python-djvulibre <= 0.3.9,
        # sometimes the exception is not raised.
        # Raise in manually in such case.
        if issubclass(page_job.status, djvu.decode.JobFailed):
            raise page_job.status
        size = page_job.size
        with self.get_output_image(page.n, page_job) as pfile:
            result = self._engine.recognize(pfile, language=self._options.language, details=self._options.details, uax29=self._options.uax29)
            if self._debug:
                result.save(os.path.join(self._temp_dir, '{n:06}'.format(n=page.n)))
            self.save_raw_ocr(page, result)
            [text] = self._engine.extract_text(result.as_stringio(),
                rotation=page.rotation,
                details=self._options.details,
                uax29=self._options.uax29,
                html5=self._options.html5,
                fix_utf8=self._engine.needs_utf8_fix,
                page_size=size
            )
            # It should be: (page 0 0 <width> <height> …):
            assert len(text) > 5
            return text

    def page_thread(self, pages, results, condition):
        for page in pages:
            n = page.n
            with condition:
                result = results[n]
                if result is not None:
                    # The page is being processed or has been already processed.
                    continue
                # Mark the page as taken.
                results[n] = True
            try:
                result = self.process_page(page)
            except djvu.decode.NotAvailable:
                logger.info('No image suitable for OCR.')
                result = False
            except (SystemExit, KeyboardInterrupt) as ex:
                with condition:
                    condition.notify()
                raise
            except Exception as ex:
                try:
                    interrupted_by_user = isinstance(ex, ipc.CalledProcessInterrupted) and ex.by_user
                    message = 'Exception while processing page {n}:\n{tb}'.format(
                        n=(n + 1),
                        tb=traceback.format_exc()
                    )
                    logger.error(message.rstrip())
                    if self._options.resume_on_error and not interrupted_by_user:
                        # As requested by user, don't abort on error and pretend that nothing happened.
                        results[n] = False
                        results.seen_exception = True
                        continue
                    else:
                        # The main thread will take care of aborting the application.
                        results[n] = ex
                        return
                finally:
                    with condition:
                        condition.notify()
            with condition:
                assert results[n] is True
                results[n] = result
                condition.notify()

    def _process(self, path, pages=None):
        self._engine = self._options.engine
        logger.info('Processing {path}:'.format(path=utils.smart_repr(path, system_encoding)))
        document = self.new_document(djvu.decode.FileURI(path))
        document.decoding_job.wait()
        if pages is None:
            pages = list(document.pages)
        else:
            pages = [document.pages[i - 1] for i in pages]
        results = Results()
        njobs = self._options.n_jobs
        thread_limit = utils.get_thread_limit(len(pages), njobs)
        os.environ['OMP_THREAD_LIMIT'] = str(thread_limit)
        condition = threading.Condition()
        threads = [
            threading.Thread(target=self.page_thread, args=(pages, results, condition))
            for i in xrange(njobs)
        ]
        def stop_threads():
            with condition:
                for page in pages:
                    # Worker threads should not bother with processing other pages.
                    # Mark them as already taken.
                    results[page.n] = True
        for thread in threads:
            thread.start()
        sed_file = self._temp_file('ocrodjvu.djvused', auto_remove=False)
        try:
            if self._options.clear_text:
                sed_file.write('remove-txt\n')
            for page in pages:
                try:
                    file_id = page.file.id.encode(system_encoding)
                except UnicodeError:
                    pageno = page.file.n + 1
                    logger.warning('warning: cannot convert page {n} identifier to locale encoding'.format(n=pageno))
                    sed_file.write('select {n}\n'.format(n=pageno))
                else:
                    sed_file.write("select '{fileid}'\n".format(
                        fileid=file_id.replace('\\', '\\\\').replace("'", "\\'")
                    ))
                sed_file.write('set-txt\n')
                result = None
                with condition:
                    while True:
                        result = results[page.n]
                        if result is None or result is True:
                            # Result is not yet available.
                            condition.wait()
                            continue
                        results[page.n] = Ellipsis  # no longer needed
                        if isinstance(result, Exception):
                            stop_threads()
                        break
                if isinstance(result, Exception):
                    if len(threads) > 1:
                        logger.info('Waiting for other threads to finish...')
                    for thread in threads:
                        thread.join()
                    self._debug = True
                    sys.exit(errors.EXIT_FATAL)
                if result is False:
                    # No image suitable for OCR.
                    pass
                else:
                    text_zones.print_sexpr(result, sed_file)
                result = None  # no longer needed
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
        except:
            stop_threads()
            raise
        finally:
            sed_file.close()
        if results.seen_exception:
            sys.exit(errors.EXIT_NONFATAL)

    def process(self, *args, **kwargs):
        try:
            self._process(*args, **kwargs)
        except:
            # The djvused script can be valuable and should not be lost in case
            # of crash.
            self._debug = True
            raise

    def close(self):
        if self._debug:
            return self._temp_dir
        else:
            shutil.rmtree(self._temp_dir)

def main(argv=sys.argv):
    options = ArgumentParser().parse_args(argv[1:])
    context = Context()
    context.init(options)
    try:
        context.process(options.path, options.pages)
    except KeyboardInterrupt:
        logger.info('Interrupted by user.')
        sys.exit(errors.EXIT_FATAL)
    finally:
        temp_dir = context.close()
        if temp_dir is not None:
            logger.info('Intermediate files were left in the {path!r} directory.'.format(path=temp_dir))

# vim:ts=4 sts=4 sw=4 et
