.PHONY: lint typecheck test run fmt

lint:
	ruff check .

typecheck:
	mypy src

test:
	pytest

run:
	python -m cinetcg

fmt:
	ruff format .
