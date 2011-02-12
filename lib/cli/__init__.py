from .. import utils

try:
    import argparse
except ImportError, ex:
    utils.enhance_import_error(ex, 'argparse', 'python-argparse', 'http://code.google.com/p/argparse/')
    raise

# vim:ts=4 sw=4 et
