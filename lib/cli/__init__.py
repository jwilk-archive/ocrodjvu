from .. import utils

try:
    import argparse
except ImportError, ex:
    utils.enhance_import_error(ex, 'argparse', 'python-argparse', 'https://code.google.com/p/argparse/')
    raise

argparse.ArgumentParser # quieten pyflakes

# vim:ts=4 sw=4 et
