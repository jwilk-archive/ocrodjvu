#!/usr/bin/python
# encoding=UTF-8

# Copyright © 2009, 2010 Jakub Wilk <jwilk@jwilk.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

'''
*ocrodjvu* is a wrapper for OCR systems that allows you to perform OCR on `DjVu <http://djvu.org/>`_ files.
'''

classifiers = '''
Development Status :: 4 - Beta
Environment :: Console
Intended Audience :: End Users/Desktop
License :: OSI Approved :: GNU General Public License (GPL)
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 2
Topic :: Text Processing
Topic :: Multimedia :: Graphics
'''.strip().split('\n')

import glob
import os

import distutils.command
import distutils.core
from distutils.command.build import build as distutils_build
from distutils.command.sdist import sdist as distutils_sdist

from lib import version

class test(distutils.core.Command):

    description = 'run tests'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import nose
        nose.main(argv=['nosetests', '--verbose', '--all-modules', 'tests'])

class build_doc(distutils_build):

    description = 'build documentation'

    def run(self):
        if os.name != 'posix':
            return
        for xmlname in glob.glob(os.path.join('doc', '*.xml')):
            manname = os.path.splitext(xmlname)[0] + '.1'
            command = [
                'xsltproc', '--nonet',
                '--param', 'man.charmap.use.subset', '0',
                '--output', 'doc/',
                'http://docbook.sourceforge.net/release/xsl/current/manpages/docbook.xsl',
                xmlname,
            ]
            self.make_file([xmlname], manname, self.spawn, [command])
            manpages.add(manname)

class sdist(distutils_sdist):

    def run(self):
        self.run_command('build_doc')
        return distutils_sdist.run(self)

distutils_build.sub_commands[:0] = [('build_doc', None)]

os.putenv('TAR_OPTIONS', '--owner root --group root --mode a+rX')

scripts = ['ocrodjvu', 'hocr2djvused', 'djvu2hocr']

if os.name == 'posix':
    manpages = set()
    data_files = [('share/man/man1', manpages)]
else:
    data_files = []

if os.name == 'nt':
    import setuptools
    # We use setuptools/distribute to be able to have .exe wrappers.
    distutils.core.setup = setuptools.setup
    extra_args = dict(
        entry_points = dict(
            console_scripts = ['%(name)s = ocrodjvu.cli.%(name)s:main' % dict(name=name) for name in scripts]
        )
    )
else:
    extra_args = dict(scripts=scripts)

distutils.core.setup(
    name = 'ocrodjvu',
    version = version.__version__,
    license = 'GNU GPL 2',
    description = 'OCR for DjVu',
    long_description = __doc__.strip(),
    classifiers = classifiers,
    url = 'http://jwilk.net/software/ocrodjvu',
    author = 'Jakub Wilk',
    author_email = 'jwilk@jwilk.net',
    packages = ['ocrodjvu', 'ocrodjvu.engines', 'ocrodjvu.cli'],
    package_dir = dict(ocrodjvu='lib'),
    data_files = data_files,
    cmdclass = dict(test=test, sdist=sdist, build_doc=build_doc),
    **extra_args
)

# vim:ts=4 sw=4 et
