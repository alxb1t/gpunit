# The gate: the one list of the commands that say a change is done. Prose names
# `make gate` and never copies them. A new command lands through a change whose
# cut names this recipe in a task.
.PHONY: gate

gate:
# the environment, from the tracked lock; not a quality axis, hence first
	uv sync --locked
	uv run ruff format --check .
	uv run ruff check .
	uv run ty check
# offline: every provider answer is faked (0001 design D13)
	uv run pytest
	openspec validate --all --strict --no-interactive
