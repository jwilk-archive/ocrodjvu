# Copyright © 2010 Jakub Wilk <jwilk@jwilk.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

TESTS = $(wildcard *.test[0-9])
TEST_STAMPS = $(TESTS:=.stamp)

all: $(TEST_STAMPS)

clean:
	rm -f *.stamp

%.stamp: %
	./run-test $(<)
	touch $(@)

# vim:ts=4 sw=4 noet
