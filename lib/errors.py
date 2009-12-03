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

class UnknownLanguageList(Exception):

    def __init__(self):
        Exception.__init__('Unable to determine list of available languages')

class EngineNotFound(Exception):

    def __init__(self, name):
        Exception.__init__(self, 'OCR engine (%s) was not found' % name)

class SecurityConcern(Exception):

    def __init__(self):
        Exception.__init__(self, 'I refuse to process this file due to security concerns')

# vim:ts=4 sw=4 et
