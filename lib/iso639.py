# encoding=UTF-8

# Copyright © 2013 Jakub Wilk <jwilk@jwilk.net>
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
ISO 639-2 support
'''

# Reference:
# http://www.loc.gov/standards/iso639-2/php/code_list.php

# Machine-readable code list:
# http://www.loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt

_b_to_t = {
    'alb': 'sqi',
    'arm': 'hye',
    'baq': 'eus',
    'bur': 'mya',
    'chi': 'zho',
    'cze': 'ces',
    'dut': 'nld',
    'fre': 'fra',
    'geo': 'kat',
    'ger': 'deu',
    'gre': 'ell',
    'ice': 'isl',
    'mac': 'mkd',
    'mao': 'mri',
    'may': 'msa',
    'per': 'fas',
    'rum': 'ron',
    'slo': 'slk',
    'tib': 'bod',
    'wel': 'cym',
}

def b_to_t(lang):
    '''
    convert from ISO 639-2/B to 639-2/T
    '''
    if not isinstance(lang, str):
        raise TypeError
    if len(lang) != 3:
        raise ValueError
    return _b_to_t.get(lang, lang)

# vim:ts=4 sw=4 et
