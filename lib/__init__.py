from __future__ import unicode_literals
import sys

if sys.version_info < (2, 7):  # no coverage
    raise RuntimeError('Python 2.7 is required')
elif sys.version_info >= (3, 3):  # no coverage
    pass
else:
    raise RuntimeError('Python 2.X is required')

# vim:ts=4 sts=4 sw=4 et
