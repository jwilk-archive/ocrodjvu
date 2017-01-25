# encoding=UTF-8

# Copyright © 2008-2016 Jakub Wilk <jwilk@jwilk.net>
#
# This file is part of ocrodjvu.
#
# ocrodjvu is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# ocrodjvu is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
# for more details.

'''interprocess communication'''

import logging
import os
import pipes
import re
import signal

thread_safe = True
try:
    import subprocess32 as subprocess
except ImportError:  # no coverage
    import subprocess
    if os.name == 'posix':
        thread_safe = False

# CalledProcessError, CalledProcessInterrupted
# ============================================

# Protect from scanadf[0] and possibly other software that sets
# SIGCHLD to SIG_IGN.
# [0] https://bugs.debian.org/596232
if os.name == 'posix':
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)

def get_signal_names():
    signame_pattern = re.compile('^SIG[A-Z0-9]*$')
    data = dict(
        (name, getattr(signal, name))
        for name in dir(signal)
        if signame_pattern.match(name)
    )
    try:
        if data['SIGABRT'] == data['SIGIOT']:
            del data['SIGIOT']
    except KeyError:  # no coverage
        pass
    try:
        if data['SIGCHLD'] == data['SIGCLD']:
            del data['SIGCLD']
    except KeyError:  # no coverage
        pass
    return dict((no, name) for name, no in data.iteritems())

CalledProcessError = subprocess.CalledProcessError

class CalledProcessInterrupted(CalledProcessError):

    _signal_names = get_signal_names()

    def __init__(self, signal_id, command):
        Exception.__init__(self, command, signal_id)
        self.by_user = signal_id == signal.SIGINT

    def __str__(self):
        signal_name = self._signal_names.get(self.args[1], self.args[1])
        return 'Command {cmd!r} was interrupted by signal {sig}'.format(cmd=self.args[0], sig=signal_name)

del get_signal_names

# Subprocess
# ==========

class Subprocess(subprocess.Popen):

    @classmethod
    def override_env(cls, override):
        env = os.environ
        # We'd like to:
        # - preserve LC_CTYPE (which is required by some DjVuLibre tools),
        # - but reset all other locale settings (which tend to break things).
        lc_ctype = env.get('LC_ALL') or env.get('LC_CTYPE') or env.get('LANG')
        env = dict(
            (k, v)
            for k, v in env.iteritems()
            if not (k.startswith('LC_') or k in ('LANG', 'LANGUAGE'))
        )
        if lc_ctype:
            env['LC_CTYPE'] = lc_ctype
        if override:
            env.update(override)
        return env

    def __init__(self, *args, **kwargs):
        kwargs['env'] = self.override_env(kwargs.get('env'))
        if os.name == 'posix':
            kwargs.update(close_fds=True)
        try:
            commandline = kwargs['args']
        except KeyError:
            commandline = args[0]
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(' '.join(pipes.quote(s) for s in commandline))
        self.__command = commandline[0]
        try:
            subprocess.Popen.__init__(self, *args, **kwargs)
        except EnvironmentError as ex:
            ex.filename = self.__command
            raise

    def wait(self, *args, **kwargs):
        return_code = subprocess.Popen.wait(self, *args, **kwargs)
        if return_code > 0:
            raise CalledProcessError(return_code, self.__command)
        if return_code < 0:
            raise CalledProcessInterrupted(-return_code, self.__command)

# PIPE
# ====

PIPE = subprocess.PIPE

# logging support
# ===============

logger = logging.getLogger('ocrodjvu.ipc')

# __all__
# =======

__all__ = [
    'CalledProcessError', 'CalledProcessInterrupted',
    'Subprocess', 'PIPE',
    'thread_safe',
]

# vim:ts=4 sts=4 sw=4 et
