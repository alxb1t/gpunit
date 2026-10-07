# The gate: the one list of the commands that say a change is done. Prose names
# `make gate` and never copies them. A new command lands through a change whose
# cut names this recipe in a task.
.PHONY: gate live

gate:
# the environment, from the tracked lock; not a quality axis, hence first
	uv sync --locked
	uv run ruff format --check .
	uv run ruff check .
	uv run ty check
# offline: every provider answer is faked (0001 design D13)
	uv run pytest
	openspec validate --all --strict --no-interactive

# The metered proof: one real pod, run by hand, its price printed first (0001 design D14).
# Not part of the gate: it rents a pod with RUNPOD_API_KEY.
live:
	@uv run python -c 'from pathlib import Path; from gpunit.runpod import RunPod; from gpunit.spec import load_spec; s = load_spec(Path("live/gpunit.toml")); p = RunPod(); h = {c: p.gpu(c).hourly for c in s.gpus}; [print(f"{c}: $${v}/h") for c, v in h.items()]; print(f"at most $${max(h.values()) * s.ceiling_s / 3600:.2f} for {s.ceiling_s}s")'
	uv run gpunit run --spec live/gpunit.toml -- sh -c '$$GPUNIT_SSH nvidia-smi'
	uv run gpunit status --spec live/gpunit.toml
