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
# The trap deletes the volume on any exit, and keeps a failed delete's exit.
live-volume:
	@uv run python live/price.py live/gpunit.volume.toml
	@set -eu; trap 'code=$$?; uv run gpunit volume down --spec live/gpunit.volume.toml || code=1; exit $$code' EXIT; \
	uv run gpunit volume up --spec live/gpunit.volume.toml --yes; \
	wrote=$$(uv run gpunit run --spec live/gpunit.volume.toml -- \
	  sh -c '$$GPUNIT_SSH "date -u +%FT%TZ | tee /runpod-volume/proof"'); \
	back=$$(uv run gpunit run --spec live/gpunit.volume.toml -- \
	  sh -c '$$GPUNIT_SSH cat /runpod-volume/proof'); \
	echo "wrote: $$wrote"; echo "read: $$back"; \
	test -n "$$wrote" && test "$$wrote" = "$$back"
	uv run gpunit status --spec live/gpunit.volume.toml

# The serve proof: the endpoint for one curl and one tool call, then a chat of one prompt
# (0005 design D9, 0008 design D4), inside the row's window volume (0010 design D10): the
# endpoint downloads the weights into it, the chat's new pod loads them from it. Not part of
# the gate: each session rents one of the row's cards with RUNPOD_API_KEY, for at most 30m
# plus the 1200s wait for SSH; the volume bills for at most 1h.
# The chat extends the window first: its 30m and 1200s must fit inside the volume's end.
# SIGTERM ends the endpoint: an `&` job starts with SIGINT ignored.
live-serve:
	@set -eu; out=$$(mktemp); \
	trap 'code=$$?; rm -f "$$out"; uv run gpunit volume down --serve $(MODEL) || code=1; exit $$code' EXIT; \
	uv run gpunit volume up --serve $(MODEL) --ceiling 1h --yes; \
	uv run gpunit serve $(MODEL) --ceiling 30m --yes --api > "$$out" & pid=$$!; \
	until grep -q '^OPENAI_API_KEY=' "$$out"; do kill -0 $$pid || { wait $$pid; exit 1; }; sleep 5; done; \
	base=$$(sed -n 's/^OPENAI_BASE_URL=//p' "$$out"); key=$$(sed -n 's/^OPENAI_API_KEY=//p' "$$out"); \
	printf 'Authorization: Bearer %s\n' "$$key" | \
	curl -sS --fail -m 300 "$$base/chat/completions" -H @- -H 'Content-Type: application/json' \
	  -d '{"model": "$(MODEL)", "messages": [{"role": "user", "content": "Say hello in one word."}], "chat_template_kwargs": {"enable_thinking": false}}' \
	  || { kill -TERM $$pid; wait $$pid || true; exit 1; }; \
	echo; OPENAI_API_KEY="$$key" uv run python live/tool_call.py "$$base" $(MODEL) \
	  || { kill -TERM $$pid; wait $$pid || true; exit 1; }; \
	kill -TERM $$pid; wait $$pid || true; \
	uv run gpunit volume up --serve $(MODEL) --ceiling 1h --yes; \
	echo 'What is 2 + 2? Answer with the number.' | uv run gpunit serve $(MODEL) --ceiling 30m --yes

# The dead-boot proof: a container that exits at once ends `up`'s wait (0006 design D6).
# Not part of the gate: it rents a pod with RUNPOD_API_KEY, for at most its 120s wait.
# `up` must exit 1 and say why; status runs either way, to show no pod is left. RunPod may
# restart the container, so the reason can be the wait's deadline (0010 design D10).
live-dead:
	@uv run python live/price.py live/gpunit.dead.toml
	@set -u; start=$$(date +%s); run=$$(mktemp -d); trap 'rm -rf "$$run"' EXIT; \
	{ uv run gpunit up --spec live/gpunit.dead.toml; echo $$? > "$$run/code"; } 2>&1 | tee "$$run/err"; \
	code=$$(cat "$$run/code"); \
	echo "up exited $$code after $$(( $$(date +%s) - start ))s"; \
	echo "reason: $$(sed -n 's/^[^ ]* refused: //p' "$$run/err" | tail -n 1)"; \
	uv run gpunit status --spec live/gpunit.dead.toml; \
	test $$code -eq 1 && grep -q ' refused: ' "$$run/err"

# The dead-serve proof: a model vLLM refuses ends `serve`'s wait, and the pod's log reaches
# the laptop (0009 design D7), inside qwen3-4b's window volume (0010 design D10). Not part of
# the gate: it rents one of qwen3-4b's cards with RUNPOD_API_KEY, for at most 600s plus the
# 1200s wait for SSH, and the volume for at most 1h; `serve` prints the price first.
live-serve-dead:
	@set -eu; \
	trap 'code=$$?; uv run gpunit volume down --serve qwen3-4b || code=1; exit $$code' EXIT; \
	uv run gpunit volume up --serve qwen3-4b --ceiling 1h --yes; \
	uv run python live/serve_dead.py
