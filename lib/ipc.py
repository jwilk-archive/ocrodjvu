# encoding=UTF-8
# Copyright © 2008, 2009 Jakub Wilk <jwilk@jwilk.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

import os
import re
import signal
import subprocess

PIPE = subprocess.PIPE

try:
    from subprocess import CalledProcessError
except ImportError:
    class CalledProcessError(Exception):
        def __init__(self, return_code, command):
            Exception.__init__(self, command, return_code)
        def __str__(self):
            return 'Command %r returned non-zero exit status %d' % self.args

_signame_pattern = re.compile('^SIG[A-Z0-9]*$')

class CalledProcessInterrupted(CalledProcessError):

    _signal_names = dict(
        (getattr(signal, name), name)
        for name in dir(signal)
        if _signame_pattern.match(name)
    )

    def __init__(self, signal_id, command):
        Exception.__init__(self, command, signal_id)
    def __str__(self):
        signal_name = self._signal_names.get(self.args[1], self.args[1])
        return 'Command %r was interrputed by signal %s' % (self.args[0], signal_name)

del _signame_pattern

class Subprocess(subprocess.Popen):

    def __init__(self, *args, **kwargs):
        subprocess.Popen.__init__(self, *args, **kwargs)
        if os.name == 'posix':
            kwargs.update(close_fds=True)
        try:
            self.__command = kwargs['args'][0]
        except KeyError:
            self.__command = args[0][0]

    def wait(self):
        return_code = subprocess.Popen.wait(self)
        if return_code > 0:
            raise CalledProcessError(return_code, self.__command)
        if return_code < 0:
            raise CalledProcessInterrupted(-return_code, self.__command)

# vim:ts=4 sw=4 et
