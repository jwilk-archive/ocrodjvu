# encoding=UTF-8

# Copyright © 2009-2018 Jakub Wilk <jwilk@jwilk.net>
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

'''
*ocrodjvu* is a wrapper for OCR systems that allows you to perform OCR on `DjVu <http://djvu.org/>`_ files.
'''

exec b''  # Python 2.6 or 2.7 is required

import glob
import os

import distutils.command
import distutils.core
from distutils.command.sdist import sdist as distutils_sdist

try:
    import distutils644
except ImportError:
    pass
else:
    distutils644.install()

def get_version():
    with open('doc/changelog', 'r') as file:
        line = file.readline()
    return line.split()[1].strip('()')

classifiers = '''
Development Status :: 4 - Beta
Environment :: Console
Intended Audience :: End Users/Desktop
License :: OSI Approved :: GNU General Public License (GPL)
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 2
Programming Language :: Python :: 2.6
Programming Language :: Python :: 2.7
Topic :: Text Processing
Topic :: Multimedia :: Graphics
'''.strip().splitlines()

class test(distutils.core.Command):

    description = 'run tests'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import nose
        nose.main(argv=['nosetests', '--verbose', 'tests'])

class sdist(distutils_sdist):

    manpage_stamp = '''.\\" [created by setup.py sdist]\n'''

    def run(self):
        raise NotImplementedError

scripts = ['ocrodjvu', 'hocr2djvused', 'djvu2hocr']

data_files = []
if os.name == 'posix':
    data_files += [('share/man/man1', glob.glob('doc/*.1'))]

if os.name == 'nt':
    import setuptools
    # We use setuptools to be able to have .exe wrappers.
    distutils.core.setup = setuptools.setup
    extra_args = dict(
        entry_points=dict(
            console_scripts=['{name} = ocrodjvu.cli.{name}:main'.format(name=name) for name in scripts]
        )
    )
else:
    extra_args = dict(scripts=scripts)

distutils.core.setup(
    name='ocrodjvu',
    version=get_version(),
    license='GNU GPL 2',
    description='OCR for DjVu',
    long_description=__doc__.strip(),
    classifiers=classifiers,
    url='http://jwilk.net/software/ocrodjvu',
    author='Jakub Wilk',
    author_email='jwilk@jwilk.net',
    packages=['ocrodjvu', 'ocrodjvu.engines', 'ocrodjvu.cli'],
    package_dir=dict(ocrodjvu='lib'),
    data_files=data_files,
    cmdclass=dict(
        sdist=sdist,
        test=test,
    ),
    **extra_args
)

# vim:ts=4 sts=4 sw=4 et
