lint:
	uv run mypy --ignore-missing-imports source
	uv run ruff check source

BASE_NAME = input/Arslan-Kürdilihicazkar-Taksim
SCRIPT = source/main.py

record:
	uv run record_cli.py $(SCRIPT) $(BASE_NAME).mp4 $(BASE_NAME).wav
run:
	uv run $(SCRIPT)
run-cli:
	uv run $(SCRIPT) $(BASE_NAME).wav
