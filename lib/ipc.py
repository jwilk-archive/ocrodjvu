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

from subprocess import CalledProcessError

# Protect from scanadf[0] and possibly other brain-dead software that set
# SIGCHLD to SIG_IGN.
# [0] http://bugs.debian.org/596232
signal.signal(signal.SIGCHLD, signal.SIG_DFL)

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
    def __str__(self):
        signal_name = self._signal_names.get(self.args[1], self.args[1])
        return 'Command %r was interrputed by signal %s' % (self.args[0], signal_name)

del get_signal_names

class Subprocess(subprocess.Popen):

    def __init__(self, *args, **kwargs):
        env_override = kwargs.pop('env', {})
        if env_override.get('LC_ALL', '') is None:
            # Reset all locale variables
            env = dict(
                (k, v)
                for k, v in os.environ.iteritems()
                if not (k.startswith('LC_') or k in ('LANG', 'LANGUAGES'))
            )
            del env_override['LC_ALL']
        else:
            env = dict(os.environ)
        env.update(env_override)
        kwargs['env'] = env
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
