# The gate: the one list of the commands that say a change is done. Prose names
# `make gate` and never copies them. A new command lands through a change whose
# cut names this recipe in a task.
.PHONY: gate live live-volume live-serve live-dead live-serve-dead

# The row `make live-serve` proves: e.g. `make live-serve MODEL=qwen3.8-27b`.
MODEL ?= qwen3-4b

gate:
# the environment, from the tracked lock; not a quality axis, hence first
	uv sync --locked
	uv run ruff format --check .
	uv run ruff check .
	uv run ty check
# boot.py runs on the pod's 3.10: ty alone catches a newer stdlib name (0012 design D7)
	uv run ty check --python-version 3.10 boot/boot.py
# offline: every provider answer is faked (0001 design D13); boot.py at 100 % coverage
	uv run pytest --cov
	openspec validate --all --strict --no-interactive

# The metered proof: one real pod, run by hand, its price printed first (0001 design D14).
# Not part of the gate: it rents a pod with RUNPOD_API_KEY.
live:
	@uv run python live/price.py
	uv run gpunit run --spec live/gpunit.toml -- sh -c '$$GPUNIT_SSH nvidia-smi'
	uv run gpunit status --spec live/gpunit.toml

# The window proof: one pod writes the UTC time to the volume, a second pod reads it back
# (0010 design D10). Not part of the gate: it rents a 10 GB volume for at most 30m and two
# pods for at most 10m each plus their 420s wait for SSH, with RUNPOD_API_KEY.
# live/window.py deletes the volume however the run ends, and a failed delete fails it.
live-volume:
	uv run python live/volume.py

# The serve proof: the endpoint for one chat request and one tool call, then a chat of one
# prompt, inside the row's window volume (0005 design D9, 0008 design D4, 0010 design D10).
# Not part of the gate: each session rents one of the row's cards with RUNPOD_API_KEY, for
# at most 30m plus the 1200s wait for SSH; the volume bills for at most 1h.
live-serve:
	uv run python live/serve.py $(MODEL)

# The dead-boot proof: a container that exits at once ends `up`'s wait (0006 design D6).
# Not part of the gate: it rents a pod with RUNPOD_API_KEY, for at most its 120s wait.
# `up` must exit 1 and say why; `down` runs however it ends, then status, to show no pod is left.
live-dead:
	uv run python live/dead.py

# The dead-serve proof: a model vLLM refuses ends `serve`'s wait, and the pod's log reaches
# the laptop (0009 design D7), inside qwen3-4b's window volume (0010 design D10). Not part of
# the gate: it rents one of qwen3-4b's cards with RUNPOD_API_KEY, for at most 600s plus the
# 1200s wait for SSH, and the volume for at most 1h; `serve` prints the price first.
live-serve-dead:
	uv run python live/serve_dead.py
