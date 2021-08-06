# encoding=UTF-8

# Copyright © 2010-2019 Jakub Wilk <jwilk@jwilk.net>
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

from __future__ import print_function
from __future__ import unicode_literals

from builtins import str
from builtins import object
import errno
import os
import signal
import stat
import codecs
import sys
import locale

from tests.tools import (
    assert_equal,
    assert_false,
    assert_raises,
    assert_true,
    interim_environ,
)

from lib import ipc
from lib import temporary

class test_exceptions(object):

    def test_sigint(self):
        ex = ipc.CalledProcessInterrupted(signal.SIGINT, 'eggs')
        assert_equal(str(ex), "Command 'eggs' was interrupted by signal SIGINT")
        assert_true(ex.by_user)

    def test_sigabrt(self):
        ex = ipc.CalledProcessInterrupted(signal.SIGABRT, 'eggs')
        assert_equal(str(ex), "Command 'eggs' was interrupted by signal SIGABRT")
        assert_false(ex.by_user)

    def test_sigsegv(self):
        ex = ipc.CalledProcessInterrupted(signal.SIGSEGV, 'eggs')
        assert_equal(str(ex), "Command 'eggs' was interrupted by signal SIGSEGV")
        assert_false(ex.by_user)

    def test_invalid_signo(self):
        # signal.NSIG is guaranteed not be a correct signal number
        ex = ipc.CalledProcessInterrupted(signal.NSIG, 'eggs')
        assert_equal(str(ex), "Command 'eggs' was interrupted by signal {0}".format(signal.NSIG))
        assert_false(ex.by_user)

def test_init_exc():
    # https://bugs.python.org/issue32490
    prog = 'ocrodjvu-nonexistent'
    with assert_raises(EnvironmentError) as ecm:
        ipc.Subprocess([prog])
    msg = '[Errno {err}] {strerr}: {prog!r}'.format(
        err=errno.ENOENT,
        strerr=os.strerror(errno.ENOENT),
        prog=prog
    )
    assert_equal(str(ecm.exception), msg)

class test_wait(object):

    def test0(self):
        child = ipc.Subprocess(['true'])
        child.wait()

    def test1(self):
        child = ipc.Subprocess(['false'])
        with assert_raises(ipc.CalledProcessError) as ecm:
            child.wait()
        message = str(ecm.exception)
        if message[-1] == '.':  # subprocess32 >= 3.5
            message = message[:-1]
        assert_equal(message, "Command 'false' returned non-zero exit status 1")

    def _test_signal(self, name):
        child = ipc.Subprocess(['cat'], stdin=ipc.PIPE)  # Any long-standing process would do.
        os.kill(child.pid, getattr(signal, name))
        with assert_raises(ipc.CalledProcessInterrupted) as ecm:
            child.wait()
        assert_equal(str(ecm.exception), "Command 'cat' was interrupted by signal " + name)

    def test_wait_signal(self):
        for name in 'SIGINT', 'SIGABRT', 'SIGSEGV':
            yield self._test_signal, name

class test_environment(object):

    # https://bugs.debian.org/594385

    def test1(self):
        with interim_environ(ocrodjvu='42'):
            child = ipc.Subprocess(
                ['sh', '-c', 'printf $ocrodjvu'],
                stdout=ipc.PIPE, stderr=ipc.PIPE,
            )
            stdout, stderr = child.communicate()
            assert_equal(stdout, b'42')
            assert_equal(stderr, b'')

    def test2(self):
        with interim_environ(ocrodjvu='42'):
            child = ipc.Subprocess(
                ['sh', '-c', 'printf $ocrodjvu'],
                stdout=ipc.PIPE, stderr=ipc.PIPE,
                env={},
            )
            stdout, stderr = child.communicate()
            assert_equal(stdout, b'42')
            assert_equal(stderr, b'')

    def test3(self):
        with interim_environ(ocrodjvu='42'):
            child = ipc.Subprocess(
                ['sh', '-c', 'printf $ocrodjvu'],
                stdout=ipc.PIPE, stderr=ipc.PIPE,
                env=dict(ocrodjvu='24'),
            )
            stdout, stderr = child.communicate()
            assert_equal(stdout, b'42')
            assert_equal(stderr, b'')

    def test_path(self):
        path = os.getenv('PATH').split(':')
        with temporary.directory() as tmpdir:
            command_name = temporary.name(dir=tmpdir)
            command_path = os.path.join(tmpdir, command_name)
            with open(command_path, 'wt') as file:
                print('#!/bin/sh', file=file)
                print('printf 42', file=file)
            os.chmod(command_path, stat.S_IRWXU)
            path[:0] = [tmpdir]
            path = ':'.join(path)
            with interim_environ(PATH=path):
                child = ipc.Subprocess([command_name],
                    stdout=ipc.PIPE, stderr=ipc.PIPE,
                )
                stdout, stderr = child.communicate()
                assert_equal(stdout, b'42')
                assert_equal(stderr, b'')

    def _test_locale(self):
        child = ipc.Subprocess(['locale'],
            stdout=ipc.PIPE, stderr=ipc.PIPE
        )
        stdout, stderr = child.communicate()
        stdout = stdout.splitlines()
        stderr = stderr.splitlines()
        assert_equal(stderr, [])
        data = dict(line.split(b'=', 1) for line in stdout)
        has_lc_all = has_lc_ctype = has_lang = 0
        for key, value in data.items():
            if key == b'LC_ALL':
                has_lc_all = 1
                assert_equal(value, b'')
            elif key == b'LC_CTYPE':
                has_lc_ctype = 1
                assert_equal(value, b'en_US.UTF-8')
            elif key == b'LANG':
                has_lang = 1
                assert_equal(value, b'')
            elif key == b'LANGUAGE':
                assert_equal(value, b'')
            else:
                assert_equal(value, b'"POSIX"')
        assert_true(has_lc_all)
        assert_true(has_lc_ctype)
        assert_true(has_lang)

    def test_locale_lc_all(self):
        with interim_environ(LC_ALL='en_US.UTF-8'):
            self._test_locale()

    def test_locale_lc_ctype(self):
        with interim_environ(LC_ALL=None, LC_CTYPE='en_US.UTF-8'):
            self._test_locale()

    def test_locale_lang(self):
        with interim_environ(LC_ALL=None, LC_CTYPE=None, LANG='en_US.UTF-8'):
            self._test_locale()

class test_require(object):

    def test_ok(self):
        ipc.require('cat')

    def test_fail(self):
        prog = 'ocrodjvu-nonexistent'
        with assert_raises(OSError) as ecm:
            ipc.require(prog)
        exc_message = "[Errno {errno.ENOENT}] command not found: {cmd!r}".format(
            errno=errno,
            cmd=prog,
        )
        assert_equal(str(ecm.exception), exc_message)

# vim:ts=4 sts=4 sw=4 et

