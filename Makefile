PYTHON ?= uv run python
PYTHON_VERSION ?= 3.13
ACTIONLINT_IMAGE ?= rhysd/actionlint:1.7.12

.PHONY: check check-python test lint format ci-docker
check: check-python
	actionlint

check-python: lint test

lint:
	$(PYTHON) -m black --check adjacent tests
	$(PYTHON) -m isort --check-only adjacent tests
	$(PYTHON) -m flake8 adjacent tests

format:
	$(PYTHON) -m black adjacent tests
	$(PYTHON) -m isort adjacent tests

test:
	$(PYTHON) -m pytest

ci-docker:
	docker run --rm -v "$(CURDIR):/work:ro" -w /work -e PYTEST_ADDOPTS='-o cache_dir=/tmp/pytest-cache' -e PIP_ROOT_USER_ACTION=ignore -e UV_PROJECT_ENVIRONMENT=/tmp/venv python:$(PYTHON_VERSION) sh -c 'pip install --quiet uv && uv sync --locked && make check-python PYTHON="uv run python"'
	docker run --rm -v "$(CURDIR):/work:ro" -w /work $(ACTIONLINT_IMAGE)
