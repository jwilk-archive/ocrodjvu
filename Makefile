# Copyright © 2012-2019 Jakub Wilk <jwilk@jwilk.net>
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

PYTHON = python3

PREFIX = /usr/local
DESTDIR =

bindir = $(PREFIX)/bin
basedir = $(PREFIX)/share/ocrodjvu
mandir = $(PREFIX)/share/man

.PHONY: all
all: ;

python-exe = $(shell $(PYTHON) -c 'import sys; print(sys.executable)')

define install-script
	sed \
		-e "1 s@^#!.*@#!$(python-exe)@" \
		-e "s#^basedir = .*#basedir = '$(basedir)/'#" \
		$(1) > $(1).tmp
	install -d $(DESTDIR)$(bindir)
	install $(1).tmp $(DESTDIR)$(bindir)/$(1)
	rm $(1).tmp
endef

define install-lib
	install -d $(DESTDIR)$(basedir)/lib/$(1)
	install -p -m644 lib/$(1)/*.py $(DESTDIR)$(basedir)/lib/$(1)
endef

.PHONY: install
install: ocrodjvu
	$(PYTHON) - < lib/__init__.py  # Python version check
	$(call install-script,ocrodjvu)
	$(call install-script,hocr2djvused)
	$(call install-script,djvu2hocr)
	$(call install-lib)
	$(call install-lib,cli)
	$(call install-lib,engines)
ifeq "$(DESTDIR)" ""
	umask 022 && $(PYTHON) -m compileall -q $(basedir)/lib/
endif
ifeq "$(wildcard doc/*.1)" ""
	# run "$(MAKE) -C doc" to build the manpages
else
	install -d $(DESTDIR)$(mandir)/man1
	install -m644 doc/*.1 $(DESTDIR)$(mandir)/man1/
endif

.PHONY: test
test: ocrodjvu
	$(PYTHON) -c 'import nose; nose.main()' --verbose

.PHONY: clean
clean:
	find . -type f -name '*.py[co]' -delete
	find . -type d -name '__pycache__' -delete
	rm -f .coverage
	rm -f *.tmp

.error = GNU make is required

# vim:ts=4 sts=4 sw=4 noet
