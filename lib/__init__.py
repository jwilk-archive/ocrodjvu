import sys

if sys.version_info < (2, 5):
    raise RuntimeError('ocrodjvu requires Python >= 2.5')
if sys.version_info >= (3, 0):
    raise RuntimeError('ocrodjvu is not compatible with Python 3.X')

# vim:ts=4 sw=4 et
