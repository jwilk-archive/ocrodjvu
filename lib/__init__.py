import sys

if sys.version_info < (2, 7):  # no coverage
    raise RuntimeError('Python 2.7 is required')
if sys.version_info >= (3, 0):  # no coverage
    raise RuntimeError('Python 2.X is required')

# vim:ts=4 sts=4 sw=4 et
