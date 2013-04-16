import sys

if sys.version_info < (2, 6):
    raise RuntimeError('Python >= 2.6 is required')
if sys.version_info >= (3, 0):
    raise RuntimeError('Python 2.X is required')

# vim:ts=4 sw=4 et
