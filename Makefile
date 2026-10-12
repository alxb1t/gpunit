# The gate: the one list of the commands that say a change is done. Prose names
# `make gate` and never copies them. A new command lands through a change whose
# cut names this recipe in a task.
.PHONY: gate live live-serve live-dead

# The row `make live-serve` proves: e.g. `make live-serve MODEL=qwen3.8-27b`.
MODEL ?= qwen3-4b

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
	@uv run python live/price.py
	uv run gpunit run --spec live/gpunit.toml -- sh -c '$$GPUNIT_SSH nvidia-smi'
	uv run gpunit status --spec live/gpunit.toml

# The serve proof: the endpoint for one curl and one tool call, then a chat of one prompt
# (0005 design D9, 0008 design D4). Not part of the gate: each session rents one of the row's
# cards with RUNPOD_API_KEY, for at most 30m plus the 1200s wait for SSH.
# SIGTERM ends the endpoint: an `&` job starts with SIGINT ignored.
live-serve:
	@set -eu; out=$$(mktemp); trap 'rm -f "$$out"' EXIT; \
	uv run gpunit serve $(MODEL) --ceiling 30m --yes --api > "$$out" & pid=$$!; \
	until grep -q '^OPENAI_API_KEY=' "$$out"; do kill -0 $$pid || { wait $$pid; exit 1; }; sleep 5; done; \
	base=$$(sed -n 's/^OPENAI_BASE_URL=//p' "$$out"); key=$$(sed -n 's/^OPENAI_API_KEY=//p' "$$out"); \
	printf 'Authorization: Bearer %s\n' "$$key" | \
	curl -sS --fail -m 300 "$$base/chat/completions" -H @- -H 'Content-Type: application/json' \
	  -d '{"model": "$(MODEL)", "messages": [{"role": "user", "content": "Say hello in one word."}], "chat_template_kwargs": {"enable_thinking": false}}' \
	  || { kill -TERM $$pid; wait $$pid || true; exit 1; }; \
	echo; OPENAI_API_KEY="$$key" uv run python live/tool_call.py "$$base" $(MODEL) \
	  || { kill -TERM $$pid; wait $$pid || true; exit 1; }; \
	kill -TERM $$pid; wait $$pid || true
	echo 'What is 2 + 2? Answer with the number.' | uv run gpunit serve $(MODEL) --ceiling 30m --yes

# The dead-boot proof: a container that exits at once ends `up`'s wait (0006 design D6).
# Not part of the gate: it rents a pod with RUNPOD_API_KEY, for at most its 120s wait.
# `up` must exit 1; status runs either way, to show no pod is left.
live-dead:
	@uv run python live/price.py live/gpunit.dead.toml
	@set -u; start=$$(date +%s); \
	uv run gpunit up --spec live/gpunit.dead.toml; code=$$?; \
	echo "up exited $$code after $$(( $$(date +%s) - start ))s"; \
	uv run gpunit status --spec live/gpunit.dead.toml; \
	test $$code -eq 1
