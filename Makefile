lint:
	uv run mypy --ignore-missing-imports source
	uv run ruff check source

BASE_NAME = input/Gulzirahan-Satarim
SCRIPT = source/main.py

record:
	uv run $(SCRIPT) $(BASE_NAME).wav --record $(BASE_NAME).mp4 --fps 60

run:
	uv run $(SCRIPT)
run-cli:
	uv run $(SCRIPT) $(BASE_NAME).wav --background input/kani-karaca-1.jpg
