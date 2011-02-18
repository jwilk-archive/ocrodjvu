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

class UnknownLanguageList(Exception):

    def __init__(self):
        Exception.__init__(self, 'Unable to determine list of available languages')

class InvalidLanguageId(ValueError):

    def __init__(self, name):
        ValueError.__init__(self, 'Invalid language identifier: %s; language identifier is typically an ISO 639-2 three-letter code' % name)

class EngineNotFound(Exception):

    def __init__(self, name):
        Exception.__init__(self, 'OCR engine (%s) was not found' % name)

class MalformedOcrOutput(Exception):

    def __init__(self, message):
        Exception.__init__(self, 'Malformed OCR output: %s' % message)

class MalformedHocr(MalformedOcrOutput):

    def __init__(self, message):
        Exception.__init__(self, 'Malformed hOCR document: %s' % message)

# vim:ts=4 sw=4 et
