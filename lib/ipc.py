# encoding=UTF-8
# Copyright © 2008, 2009, 2010 Jakub Wilk <jwilk@jwilk.net>
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

from subprocess import CalledProcessError

# Protect from scanadf[0] and possibly other brain-dead software that set
# SIGCHLD to SIG_IGN.
# [0] http://bugs.debian.org/596232
try:
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)
except AttributeError:
    pass

def get_signal_names():
    _signame_pattern = re.compile('^SIG[A-Z0-9]*$')
    data = dict(
        (name, getattr(signal, name))
        for name in dir(signal)
        if _signame_pattern.match(name)
    )
    try:
        if data['SIGABRT'] == data['SIGIOT']:
            del data['SIGIOT']
    except KeyError:
        pass
    try:
        if data['SIGCHLD'] == data['SIGCLD']:
            del data['SIGCLD']
    except KeyError:
        pass
    return dict((no, name) for name, no in data.iteritems())

class CalledProcessInterrupted(CalledProcessError):

    _signal_names = get_signal_names()

    def __init__(self, signal_id, command):
        Exception.__init__(self, command, signal_id)
        self.by_user = signal_id == signal.SIGINT

    def __str__(self):
        signal_name = self._signal_names.get(self.args[1], self.args[1])
        return 'Command %r was interrupted by signal %s' % (self.args[0], signal_name)

del get_signal_names

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
            self.__command = kwargs['args'][0]
        except KeyError:
            self.__command = args[0][0]
        subprocess.Popen.__init__(self, *args, **kwargs)

    def wait(self):
        return_code = subprocess.Popen.wait(self)
        if return_code > 0:
            raise CalledProcessError(return_code, self.__command)
        if return_code < 0:
            raise CalledProcessInterrupted(-return_code, self.__command)

# vim:ts=4 sw=4 et
