.PHONY: check help clean format install install-dev install-pipx uninstall uninstall-pipx

PACKAGE_NAME ?= ap_copy_master_to_blink
PROJECT_NAME ?= ap-copy-master-to-blink

ifeq ($(OS),Windows_NT)
    VENV_DIR ?= .venv
    PYTHON ?= $(VENV_DIR)/Scripts/python.exe
else
    VENV_DIR ?= .venv
    PYTHON ?= $(VENV_DIR)/bin/python
endif

# Interpreter used to bootstrap the venv. CI overrides to `python` so
# the venv is pinned to the matrix Python installed by setup-python
# instead of the container's system python3 (see build/makefile.md).
PY_SYS ?= python3

# Test targets are pulled into make/test.mk for readability.
-include make/test.mk

$(info venv: $(VENV_DIR))

check: test-format test-lint test-typecheck test-unit test-coverage  ## Run full quality gate (default)

.DEFAULT_GOAL := check

help:  ## Show available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-32s\033[0m %s\n", $$1, $$2}'

$(PYTHON):
	$(PY_SYS) -m venv $(VENV_DIR)

clean:  ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

format: install-dev  ## Rewrite sources with black
	$(PYTHON) -m black $(PACKAGE_NAME) tests

install: $(PYTHON)  ## Install into the local venv
	$(PYTHON) -m pip install .

install-dev: $(PYTHON)  ## Editable install + dev extras
	$(PYTHON) -m pip install -e ".[dev]"

install-pipx:  ## Install globally via pipx
	python3 -m pipx install . --force

uninstall: $(PYTHON)  ## Uninstall from the local venv
	$(PYTHON) -m pip uninstall -y $(PROJECT_NAME)

uninstall-pipx:  ## Uninstall the pipx install
	python3 -m pipx uninstall $(PROJECT_NAME)
