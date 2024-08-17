lint:
	mypy --ignore-missing-imports .
	ruff check .

BASE_NAME = input/tunar-nihavend-taksim
SCRIPT = source/main.py

record:
	python record_cli.py $(SCRIPT) $(BASE_NAME).mp4 $(BASE_NAME).wav

run:
	python $(SCRIPT) $(BASE_NAME).wav
