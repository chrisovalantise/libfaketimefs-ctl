# http://clarkgrubb.com/makefile-style-guide

MAKEFLAGS += --warn-undefined-variables --no-print-directory
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := test
.DELETE_ON_ERROR:
.SUFFIXES:

-include .env.upload
export GH_TOKEN
export GITHUB_TOKEN
export GITHUB_REPOSITORY
export GITHUB_TAG

################
# Python build #
################

PYTHON ?= python3
UV ?= uv

UV_TOOL_RUN := $(UV) run --no-project
GITHUB_REPOSITORY ?= chrisovalantise/libfaketimefs-ctl

.PHONY: test
test:
	PYTHONPATH=$(CURDIR) $(UV_TOOL_RUN) --with . $(PYTHON) -c "import doctest, libfaketimefs_ctl; raise SystemExit(doctest.testmod(libfaketimefs_ctl).failed)"
	PYTHONPATH=$(CURDIR) $(UV_TOOL_RUN) --with . --with pytest pytest
	$(UV_TOOL_RUN) --with flake8 flake8 bin/libfaketimefs-ctl libfaketimefs_ctl/*.py

.PHONY: build
build:
	$(UV) build

.PHONY: upload
upload: build
	@test -n "$${GH_TOKEN:-$${GITHUB_TOKEN:-}}" || (echo "Set GH_TOKEN or GITHUB_TOKEN with repo write access" >&2; exit 1)
	@token="$${GH_TOKEN:-$${GITHUB_TOKEN:-}}"; \
	repo="$(GITHUB_REPOSITORY)"; \
	tag="$${GITHUB_TAG:-v$$($(UV) version --short)}"; \
	api="https://api.github.com/repos/$${repo}"; \
	upload_api="https://uploads.github.com/repos/$${repo}/releases"; \
	release_json=$$(curl -fsS \
		-H "Authorization: Bearer $${token}" \
		-H "Accept: application/vnd.github+json" \
		"$${api}/releases/tags/$${tag}" 2>/dev/null || true); \
	if [ -z "$${release_json}" ]; then \
		echo "Creating GitHub release $${repo}@$${tag}"; \
		release_json=$$(curl -fsS -X POST \
			-H "Authorization: Bearer $${token}" \
			-H "Accept: application/vnd.github+json" \
			"$${api}/releases" \
			-d "$$(printf '{"tag_name":"%s","name":"%s","body":"%s"}' "$${tag}" "$${tag}" "Built Python artifacts for $${tag}")"); \
	else \
		echo "Using existing GitHub release $${repo}@$${tag}"; \
	fi; \
	release_id=$$(printf '%s' "$${release_json}" | $(PYTHON) -c 'import json,sys; print(json.load(sys.stdin)["id"])'); \
	for artifact in dist/*; do \
		name=$$(basename "$${artifact}"); \
		echo "Uploading $${name}"; \
		existing_asset_id=$$(curl -fsS \
				-H "Authorization: Bearer $${token}" \
				-H "Accept: application/vnd.github+json" \
				"$${api}/releases/$${release_id}/assets" | \
				ASSET_NAME="$${name}" $(PYTHON) -c 'import json,sys,os; name=os.environ["ASSET_NAME"]; print(next((str(a["id"]) for a in json.load(sys.stdin) if a["name"] == name), ""))'); \
		if [ -n "$${existing_asset_id}" ]; then \
			curl -fsS -X DELETE \
				-H "Authorization: Bearer $${token}" \
				-H "Accept: application/vnd.github+json" \
				"$${api}/releases/assets/$${existing_asset_id}" >/dev/null; \
		fi; \
		curl -fsS -X POST \
			-H "Authorization: Bearer $${token}" \
			-H "Accept: application/vnd.github+json" \
			-H "Content-Type: application/octet-stream" \
			--data-binary @"$${artifact}" \
			"$${upload_api}/$${release_id}/assets?name=$${name}" >/dev/null; \
	done

.PHONY: clean
clean:
	rm -rf build dist *.egg-info .venv
