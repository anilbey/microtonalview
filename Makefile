static-checks:
	mypy --ignore-missing-imports .
	ruff check .
