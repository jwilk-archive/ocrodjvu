# Copyright © 2018-2019 Jakub Wilk <jwilk@jwilk.net>
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

rst2xml = $(notdir $(shell command -v rst2xml || echo rst2xml.py)) \
	--input-encoding=UTF-8 \
	--strict

xsl = http://docbook.sourceforge.net/release/xsl/current/manpages/docbook.xsl
xsltproc = xsltproc --nonet \
	--param man.authors.section.enabled 0 \
	--param man.charmap.use.subset 0 \
	--param man.font.links '"I"'

xml-files = $(wildcard *.xml)
man-files = $(xml-files:.xml=.1)

.PHONY: all
all: $(man-files)

%.1: %.xml
	$(xsltproc) $(xsl) $(<)
	perl -pi -e 's#^(\\%https?://.*)#\\m[blue]\\fI$$1\\fR\\m[]#' $(@)

.PHONY: check
check: check-changelog check-rst check-xml

.PHONY: check-changelog
check-changelog: changelog
	dpkg-parsechangelog -l$(<) --all 2>&1 >/dev/null | { ! grep .; }

.PHONY: check-rst
check-rst:
	grep -rwl 'ft[=]rst' | xargs -t -I{} $(rst2xml) {} /dev/null

.PHONY: check-xml
check-xml: $(xml-files)
	xmllint --nonet --noout --valid $(^)

.PHONY: clean
clean:
	rm -f *.1

# vim:ts=4 sts=4 sw=4 noet
