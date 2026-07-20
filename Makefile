# http://clarkgrubb.com/makefile-style-guide

MAKEFLAGS += --warn-undefined-variables --no-print-directory
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := test
.DELETE_ON_ERROR:
.SUFFIXES:

################
# Python build #
################

PYTHON ?= python3
UV ?= uv

UV_TOOL_RUN := $(UV) run --no-project

.PHONY: test
test:
	PYTHONPATH=$(CURDIR) $(UV_TOOL_RUN) --with . $(PYTHON) -c "import doctest, libfaketimefs_ctl; raise SystemExit(doctest.testmod(libfaketimefs_ctl).failed)"
	PYTHONPATH=$(CURDIR) $(UV_TOOL_RUN) --with . --with pytest pytest
	$(UV_TOOL_RUN) --with flake8 flake8 bin/libfaketimefs-ctl libfaketimefs_ctl/*.py

.PHONY: build
build:
	$(UV) build

.PHONY: clean
clean:
	rm -rf build dist *.egg-info .venv
