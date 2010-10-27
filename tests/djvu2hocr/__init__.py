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

from __future__ import with_statement

import glob
import os
import re
import shlex
import shutil

from ocrodjvu.cli import djvu2hocr
from ocrodjvu import temporary
from ocrodjvu import ipc

from tests.common import *

def do(test_filename, djvused_filename, index):
    with open(test_filename, 'rb') as file:
        commandline = file.readline()
        expected_output = file.read()
    args = shlex.split(commandline)
    assert args[0] == '#'
    with temporary.directory() as tmpdir:
        djvu_filename = os.path.join(tmpdir, 'empty.djvu')
        args += [djvu_filename]
        shutil.copy(
            os.path.join(os.path.dirname(__file__), '..', 'common', 'empty.djvu'),
            djvu_filename)
        ipc.Subprocess(['djvused', '-f', djvused_filename, '-s', djvu_filename]).wait()
        xml_filename = os.path.join(tmpdir, 'output.html')
        with open(xml_filename, 'w+b') as xml_file:
            xmllint = ipc.Subprocess(['xmllint', '--format', '-'], stdin=ipc.PIPE, stdout=xml_file)
            try:
                with open(os.devnull, 'w') as null:
                    djvu2hocr.main(args, stdout=xmllint.stdin, stderr=null)
            finally:
                xmllint.stdin.close()
                try:
                    xmllint.wait()
                except ipc.CalledProcessError:
                    # Raising the exception here is likely to hide the real
                    # reason of the failure.
                    pass
            xml_file.seek(0)
            output = xml_file.read()
    assert_ml_equal(output, expected_output)

def list_tests():
    for test_filename in glob.glob(os.path.join(os.path.dirname(__file__), '*.test[0-9]')):
        index = int(test_filename[-1])
        base_filename = test_filename[:-6]
        djvused_filename = base_filename + '.djvused'
        func_name = 'test_%s_t%d' % (re.sub(r'\W+', '_', os.path.basename(base_filename)), index)
        def func(test_filename=test_filename, djvused_filename=djvused_filename, index=index):
            do(test_filename, djvused_filename, index)
        func.__name__ = func_name
        yield func_name, func

globals().update(dict(list_tests()))

del list_tests

# vim:ts=4 sw=4 et
