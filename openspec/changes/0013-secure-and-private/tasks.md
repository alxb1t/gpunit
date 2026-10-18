# Tasks — 0013 secure and private

The laptop's fixes, the tunnel, placement, serve's logging, the `0012` cards and the docs, then the metered probe, per
[design](design.md). Every new test carries `@pytest.mark.spec` with the key its task names.

## Progress

- [x] 1 — The laptop
- [x] 2 — The tunnel
- [x] 3 — Placement
- [x] 4 — Serve
- [x] 5 — The cards
- [ ] 6 — The docs
- [ ] 7 — ⚠️ **HUMAN · METERED** — the probe

## 1 — The laptop

- [x] 1.1 **HALT CHECK** — none of this change exists yet, the cards it closes are in the backlog, and the draft [D14](design.md#d14) copies is on disk.
  Verify: `grep -c -E 'RUNPOD_|datacenters' gpunit/spec.py` prints `0`, `grep -c 'enable-log-requests' gpunit/serve/models.toml` prints `0`, `test -e docs/threat-model.md; echo $?` prints `1`, `grep -c -E '^- \*\*0012·R[3-9] ' .minions/backlog.md` prints `7`, and `test -f openspec/changes/0013-secure-and-private/threat-model-draft.md; echo $?` prints `0`.
- [x] 1.2 Drop `RUNPOD_API_KEY` from `run`'s command environment in `gpunit/run.py`, per [D1](design.md#d1); bind `run:handover:no-account-key` in `tests/test_run.py`.
  Verify: `grep -c '"run:handover:no-account-key"' tests/test_run.py` prints `1`, and `uv run pytest -q tests/test_run.py` exits 0.
- [x] 1.3 Refuse `RUNPOD_*` names in `gpunit/spec.py`'s `_env`, per [D2](design.md#d2); bind `spec:file:env-runpod-refused` in `tests/test_spec.py` and `spec:file:env-secret-reference-kept` in `tests/test_runpod.py`.
  Verify: `grep -c '"spec:file:env-runpod-refused"' tests/test_spec.py` prints `1`, `grep -c '"spec:file:env-secret-reference-kept"' tests/test_runpod.py` prints `1`, and `uv run pytest -q tests/test_spec.py tests/test_runpod.py` exits 0.
- [x] 1.4 Set `.gpunit/` to `0700` in `State._mkdir`, `gpunit/state.py`, per [D3](design.md#d3); bind `session:key:dir-private` in `tests/test_state.py`.
  Verify: `grep -c 'self.dir.chmod(0o700)' gpunit/state.py` prints `1`, and `uv run pytest -q tests/test_state.py` exits 0.
- [x] 1.5 Add `log.clean` to `gpunit/log.py` and use it at `gpunit/serve/session.py:229` and `:267`, per [D4](design.md#d4); bind `serve:wait:log-lines-cleaned` in `tests/test_serve_session.py`.
  Verify: `grep -c 'log.clean(' gpunit/serve/session.py` prints `2`, `grep -c '"serve:wait:log-lines-cleaned"' tests/test_serve_session.py` prints a number of at least `1`, and `uv run pytest -q tests/test_serve_session.py` exits 0.

## 2 — The tunnel

- [x] 2.1 Add `_taken` to `gpunit/library.py`, use it in `_refuse_busy_ports` and again before the tunnel opens, per [D5](design.md#d5); bind `run:ports:busy-on-v6-refuses` in `tests/test_run.py` and `library:tunnel:taken-before-open-refuses` in `tests/test_library.py`.
  Verify: `grep -c '"::1"' gpunit/library.py` prints a number of at least `1`, `grep -c '"run:ports:busy-on-v6-refuses"' tests/test_run.py` prints `1`, `grep -c '"library:tunnel:taken-before-open-refuses"' tests/test_library.py` prints `1`, and `uv run pytest -q tests/test_run.py tests/test_library.py` exits 0.
- [x] 2.2 Make `_Tunnel._watch` refuse a taken port through `_Signals.refuse`, and `run._command` end its child on `log.Refusal`, per [D5](design.md#d5) and [D6](design.md#d6); bind `library:tunnel:taken-port-refuses` in `tests/test_library.py` and `run:tunnel:taken-port-refuses` in `tests/test_run.py`.
  Verify: `grep -c 'pthread_kill' gpunit/library.py` prints `1`, `grep -c '"library:tunnel:taken-port-refuses"' tests/test_library.py` prints `1`, `grep -c '"run:tunnel:taken-port-refuses"' tests/test_run.py` prints `1`, and `uv run pytest -q tests/test_run.py tests/test_library.py tests/test_serve_session.py` exits 0.

## 3 — Placement

- [x] 3.1 Load `datacenters` in `gpunit/spec.py` and refuse a `volume_datacenter` outside it, per [D7](design.md#d7); bind `spec:file:datacenters-load`, `spec:file:datacenters-empty-refused` and `spec:file:volume-datacenter-outside-refused` in `tests/test_spec.py`.
  Verify: `grep -c -E '"spec:file:(datacenters-load|datacenters-empty-refused|volume-datacenter-outside-refused)"' tests/test_spec.py` prints a number of at least `3`, and `uv run pytest -q tests/test_spec.py` exits 0.
- [x] 3.2 Add `PodInfo.datacenter` in `gpunit/provider.py`; read `dataCenterId` in `RunPod.get` and send `datacenters` in `RunPod.create`, `gpunit/runpod.py`, per [D8](design.md#d8); bind `session:datacenters:create-names-them` and `session:datacenters:unset-names-none` in `tests/test_runpod.py`.
  Verify: `grep -c '"dataCenterId"' gpunit/runpod.py` prints `1`, `grep -c -E '"session:datacenters:(create-names-them|unset-names-none)"' tests/test_runpod.py` prints a number of at least `2`, and `uv run pytest -q tests/test_runpod.py` exits 0.
- [x] 3.3 Refuse a mounted volume outside `datacenters` in `lifecycle.up`, and check the pod's data centre in `_wait`, `gpunit/lifecycle.py`, per [D8](design.md#d8); let `tests/fakes.py`'s `FakeProvider` answer a data centre; bind the `session:datacenters:` keys `volume-outside-refuses`, `pod-outside-tears-down` and `unread-is-not-yet` in `tests/test_up.py`.
  Verify: `grep -c -E '"session:datacenters:(volume-outside-refuses|pod-outside-tears-down|unread-is-not-yet)"' tests/test_up.py` prints a number of at least `3`, and `uv run pytest -q` exits 0.
- [x] 3.4 Keep `volume up`'s stock choice within `datacenters` in `gpunit/volume.py`'s `_datacenter`, per [D9](design.md#d9); bind `volume:up:datacenter-within-allow-list` and `volume:up:no-stock-in-allow-list-refuses` in `tests/test_volume.py`.
  Verify: `grep -c -E '"volume:up:(datacenter-within-allow-list|no-stock-in-allow-list-refuses)"' tests/test_volume.py` prints a number of at least `2`, and `uv run pytest -q tests/test_volume.py` exits 0.

## 4 — Serve

- [x] 4.1 Add `"--no-enable-log-requests"` to each row's `args` in `gpunit/serve/models.toml`, per [D10](design.md#d10); add it to `qwen3-4b`'s `SERVE_ARGS` in `tests/test_serve_table.py`, and bind `serve:table:request-logging-off` there.
  Verify: `grep -c '"--no-enable-log-requests"' gpunit/serve/models.toml` prints `2`, `grep -c '"serve:table:request-logging-off"' tests/test_serve_table.py` prints `1`, and `uv run pytest -q tests/test_serve_table.py tests/test_serve_session.py` exits 0.

## 5 — The cards

- [x] 5.1 Bind `test_no_ca_store_refuses_before_the_arm` and `test_a_ca_directory_alone_is_a_store` in `tests/test_boot_steps.py` to `boot:refuse:no-ca-store`, per [D11](design.md#d11) (`0012·R5`).
  Verify: `grep -c '"boot:refuse:no-ca-store"' tests/test_boot_steps.py` prints `2`, `grep -c '"boot:refuse:no-sshd"' tests/test_boot_steps.py` prints `2`, and `uv run pytest -q tests/test_boot_steps.py` exits 0.
- [x] 5.2 Reword the comment at `boot/boot.py:105`, and rename `test_no_ca_store_names_the_cause` and reword its comment in `tests/test_boot_steps.py`, per [D11](design.md#d11) (`0012·R6`).
  Verify: `grep -c 'a missing CA store' boot/boot.py` prints `0`, `grep -c 'def test_an_untrusted_certificate_names_the_cause' tests/test_boot_steps.py` prints `1`, `grep -c 'test_no_ca_store_names_the_cause' tests/test_boot_steps.py` prints `0`, and `uv run pytest -q tests/test_boot_steps.py --cov` exits 0.
- [x] 5.3 In `README.md`'s `make live-dead` paragraph, add [D11](design.md#d11)'s sentences (`0012·R8`).
  Verify: `grep -c -F 'In a checkout that records a pod it exits' README.md` prints `1`.
- [x] 5.4 Bind `test_dead_leaves_a_recorded_pod_alone` in `tests/test_live.py` to `session:wait:dead-proof-spares-a-record`, per [D11](design.md#d11) (`0012·R9`).
  Verify: `grep -B2 'def test_dead_leaves_a_recorded_pod_alone' tests/test_live.py | grep -c 'session:wait:dead-proof-spares-a-record'` prints `1`, and `uv run pytest -q tests/test_live.py` exits 0.

## 6 — The docs

- [ ] 6.1 In `README.md`, add the `datacenters` line, the `[env]` comment, step 3's sentence and `## Security and privacy`, per [D13](design.md#d13).
  Verify: `grep -c '^## Security and privacy$' README.md` prints `1`, `grep -c -E '^### (Where your data lands|Secrets|The account key|Accepted risks)$' README.md` prints `4`, `grep -c 'datacenters = \["EU-RO-1"\]' README.md` prints `1`, and `grep -c 'RUNPOD_\* names are refused here' README.md` prints `1`.
- [ ] 6.2 Write `docs/threat-model.md` from [the draft](threat-model-draft.md) in this change's directory, brought to `v0.9`'s state, per [D14](design.md#d14).
  Verify: `grep -c -E '^\| T[0-9]+ ' docs/threat-model.md` prints `54`, `grep -E '^\| T(17|21|26|30|34|39) ' docs/threat-model.md | grep -c '| mitigated |'` prints `6`, `grep -E '^\| T[0-9]+ ' docs/threat-model.md | grep '| gap |' | cut -d'|' -f2 | tr -d ' ' | paste -sd, -` prints `T22,T24,T54`, `grep -c '^## 7. The probe$' docs/threat-model.md` prints `1`, and `grep -c -E '^type: |draft' docs/threat-model.md` prints `0`.
- [ ] 6.3 In `CLAUDE.md`, name `docs/threat-model.md` in the layout and add the trust-boundary invariant, per [D14](design.md#d14).
  Verify: `grep -c 'docs/threat-model.md' CLAUDE.md` prints a number of at least `2`, and `grep -c 'touches a trust boundary' CLAUDE.md` prints `1`.

## 7 — ⚠️ **HUMAN · METERED** — the probe

- [ ] 7.1 **HUMAN · METERED** — G6: with a console-made restricted key as `RUNPOD_API_KEY`, run `make live`, `make live-volume` and `uv run gpunit spend --days 1`, widening per [D15](design.md#d15); append their tails to `live/last_run.txt`, each under `<date> — make <target>, 0013-secure-and-private`; add `- **Measured minimum:** …` to README and `- **G6 measured:** …` to `docs/threat-model.md`.
  Verify: `grep -c -E '^[0-9]{4}-[0-9]{2}-[0-9]{2} — make live(-volume)?, 0013-secure-and-private$' live/last_run.txt` prints `2`, `grep -c '^- \*\*Measured minimum:\*\* ' README.md` prints `1`, and `grep -c '^- \*\*G6 measured:\*\* ' docs/threat-model.md` prints `1`.
- [ ] 7.2 **HUMAN · METERED** — G5: run [D15](design.md#d15)'s laptop block, then its pod block on the pod's shell, `<other>` the id the laptop block prints; add `- **G5 measured:** <each path's status>` under `## 7. The probe` in `docs/threat-model.md`.
  Verify: `grep -c '^- \*\*G5 measured:\*\* ' docs/threat-model.md` prints `1`.
- [ ] 7.3 **HUMAN · METERED** — G12: compare `authorized_keys` and try `ssh.proxy`, per [D15](design.md#d15); add `- **G12 measured:** …`; set T22, T24 and T54 from the results; then [D15](design.md#d15)'s end.
  Verify: `grep -c '^- \*\*G12 measured:\*\* ' docs/threat-model.md` prints `1`, and `grep -E '^\| T(22|24|54) ' docs/threat-model.md | grep -c '| gap |'` prints `0`.
