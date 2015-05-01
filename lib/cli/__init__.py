from .. import utils

try:
    import argparse
except ImportError, ex:
    utils.enhance_import_error(ex, 'argparse', 'python-argparse', 'https://pypi.python.org/pypi/argparse')
    raise

argparse.ArgumentParser # quieten pyflakes

# vim:ts=4 sts=4 sw=4 et
