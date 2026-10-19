# Principles

The words gpunit's code and docs use, then the rules it follows: each with the decision it comes from, what holds it,
and where the code breaches it. **A rule claims no more than what holds it**: a test, a gate step, `review`, or
`nothing`. A breach names its symbol and the audit's finding.

## The words

- **session** — one pod's life for one working directory: placed, proven, used and torn down, through `up` and
  `down`, `run`, `serve` or `gpunit.session`.
- **record** — `.gpunit/pod`: the pod a session made, its address and the time of its create.
- **pending** — `.gpunit/pending`: a create was sent and no record names its pod yet; `.gpunit/volume.pending` is
  the same for a volume. **`began`** — `State.began`: this process wrote `pending` itself, so a teardown is its to
  do.
- **refusal** — gpunit declined and left nothing it rented: a `refused:` line, `gpunit.Refused`, exit `1`.
  **lost** — a create's answer did not arrive, so a pod may exist: `gpunit.Lost`, exit `3`. **teardown failed** —
  a delete did not succeed and the record is kept: `gpunit.TeardownFailed`, exit `1`.
- **the seam** — `gpunit/provider.py::Provider`, the protocol between the session and a GPU cloud.
- **the boot contract** — what the laptop tells the pod, its env, and the lines boot prints back:
  `gpunit/contract.py` and `boot/boot.py`.
- **the ceiling** — the longest a pod may live, the spec's `ceiling`; boot stops the pod there.
- **the window** — a network volume that outlives its sessions, to its own `volume_ceiling`; `.gpunit/volume`
  records it.
- **the sweep** — deleting what no record names: the project's pods in `down`, a window past its end before a
  verb's work, a lost volume create's volume in `volume down`.
- **a row** — one model `serve` knows, from `gpunit/serve/models.toml` or the user file.
- **the ledger** — `ledger.jsonl` under the home directory: each pod's and volume's project, for `spend`.
- **the price** — the most a rent can cost, printed before `serve` and `volume up` ask `y/N`.

## The rules

### Secrets

| rule | from | held by | breach |
|---|---|---|---|
| The account key travels in a request header alone: on no argv, redirect or subprocess | [D3](decisions.md#d3--runpod-on-urllib-bounded-calls-the-key-in-a-header-no-redirect-quiet-log-reads-end), [D47](decisions.md#d47--boots-stop-over-urllib-the-commands-env-without-the-key-and-the-nonce) | `test_gpu_reads_the_memory_and_the_secure_price`, `test_the_commands_end_stops_the_pod`, `test_a_redirect_is_not_followed`, `test_a_redirect_is_a_failed_stop_never_followed`, `test_the_key_comes_from_the_environment_only` | — |
| The key comes from the environment alone; no `.env` is read | [D11](decisions.md#d11--spec-from-gpunittoml-strict-keys-a-digest-a-required-ceiling-checked-ports) | `test_no_key_refuses_at_construction`, `test_a_dotenv_beside_the_spec_is_ignored` | — |
| The consumer's command gets no account key; `[env]` names no `RUNPOD_*` or `GPUNIT_*` | [D33](decisions.md#d33--runs-command-gets-the-host-the-ports-and-gpunit_ssh-never-the-account-key), [D12](decisions.md#d12--env-passes-as-written-names-no-gpunit_-or-runpod_-gpunits-names-win) | `test_the_command_gets_no_account_key`, `test_the_child_holds_no_key_and_no_nonce`, `test_a_runpod_variable_in_env_is_refused`, `test_a_gpunit_variable_in_env_is_refused` | — |
| A fresh keypair per session, private, deleted with the pod | [D16](decisions.md#d16--a-keypair-per-session-deleted-at-teardown) | `test_the_keypair_is_made_and_passed`, `test_the_key_files_are_0600`, `test_the_keypair_leaves_with_the_pod` | — |
| gpunit's ssh is its own | [D24](decisions.md#d24--gpunits-ssh-is-its-own-the-tools-checked-before-any-request) | `test_ssh_reads_no_config_and_offers_the_session_key_alone` | — |
| The host key is proven over the authenticated log before anything connects | [D22](decisions.md#d22--the-host-key-is-proven-over-the-log) | `test_a_match_is_recorded`, `test_a_mismatch_tears_down`, `test_a_key_line_the_command_echoes_is_not_the_key`, `test_a_key_line_with_another_nonce_is_not_the_key`, `test_an_older_boot_is_refused_at_once` | — |
| A taken loopback port never receives the session's traffic | [D31](decisions.md#d31--a-taken-local-port-refuses-from-any-thread-unlatched), [D30](decisions.md#d30--the-tunnel-a-watched-ssh--n--l-a-backoff-one-forward-per-loopback-family) | `test_a_taken_port_ends_the_block`, `test_each_loopback_family_is_its_own_forward` | — |
| Untrusted lines are cleaned before the terminal | [D39](decisions.md#d39--podlog-holds-the-log-since-the-create-printed-lines-are-cleaned), [D37](decisions.md#d37--the-chat-streamed-in-memory-cleaned-on-screen) | `test_printed_log_lines_are_cleaned`, `test_streamed_text_is_cleaned_and_kept_as_streamed` | `0014·S1`: a row's arguments can turn request logging back on (`0015·F23`) |

### Teardown

| rule | from | held by | breach |
|---|---|---|---|
| Teardown on every way out of the block; signals are ignored during it | [D29](decisions.md#d29--signals-raise-interrupted-once-are-ignored-during-teardown-restored-after), [D27](decisions.md#d27--session-is-a-context-manager-over-open_session-run-is-its-first-caller) | `test_the_blocks_end_tears_down`, `test_an_error_in_the_block_tears_down`, `test_sigterm_ends_the_block_and_tears_down`, `test_a_signal_during_the_teardown_is_ignored`, `test_the_deadline_tears_down`, `test_a_mismatch_tears_down` | — |
| Nothing is torn down that this session did not make | [D20](decisions.md#d20--teardown-only-when-a-create-began-here-or-was-lost), [D23](decisions.md#d23--teardown-a-404-keeps-the-record-the-projects-pods-are-swept) | `test_an_interrupt_before_the_create_sweeps_nothing`, `test_an_interrupt_beside_an_earlier_record_deletes_nothing`, `test_a_look_alike_image_is_not_ours`, `test_down_leaves_a_volume_of_its_name_it_did_not_make` | — |
| A 404 is never gone | [D23](decisions.md#d23--teardown-a-404-keeps-the-record-the-projects-pods-are-swept) | `test_a_404_keeps_the_record`, `test_a_refused_delete_keeps_the_record` | — |
| A lost create exits `3`, keeps its mark, and the next `down` finds it | [D19](decisions.md#d19--placement-the-catalogue-floor-one-create-per-card-a-400-moves-on-the-rest-is-lost), [D32](decisions.md#d32--exit-codes-0-1-2-3-128n) | `test_a_5xx_create_is_lost`, `test_a_lost_create_tears_down_and_exits_3`, `test_a_lost_create_keeps_the_pending_mark`, `test_a_lost_create_is_swept` | — |
| A dead pod ends every wait | [D21](decisions.md#d21--the-wait-a-bounded-poll-a-failed-read-is-not-yet-two-dead-polls-end-any-wait) | `test_a_dead_pod_ends_the_wait`, `test_one_dead_poll_is_not_yet`, `test_a_dead_pod_ends_the_hold` | — |
| A dead pipe on stderr ends no teardown | [D4](decisions.md#d4--gpunits-lines-utc-stamped-to-stderr-or-a-sink-refused-opens-a-refusal-a-dead-pipe-swallowed-sysexit-in-cli-alone) | `test_a_dead_pipe_on_stderr_ends_no_teardown`, `test_a_dead_pipe_on_stderr_leaves_the_process_exit_code` | — |
| A signal exits `128+n` | [D32](decisions.md#d32--exit-codes-0-1-2-3-128n) | `test_a_signal_during_the_teardown_is_ignored` and the `run` tests | breached: `gpunit/volume.py::_agree` exits `1` on Ctrl-C at the price (`0015·F20`) |

### Placement, cost and pins

| rule | from | held by | breach |
|---|---|---|---|
| One live session per project | [D15](decisions.md#d15--gpunit-in-the-working-directory-each-record-written-whole-the-directory-0700) | `test_a_recorded_pod_refuses_up`, `test_a_pending_create_refuses_up`, `test_a_listed_pod_refuses_up` | — |
| The ceiling is required, and the pod enforces it | [D11](decisions.md#d11--spec-from-gpunittoml-strict-keys-a-digest-a-required-ceiling-checked-ports), [D25](decisions.md#d25--the-pod-stops-at-its-ceiling-and-on-any-end-down-deletes) | `test_no_ceiling_no_pod`, `test_the_ceiling_reaches_the_pod_in_seconds`, `test_the_watchdog_stops_the_pod_at_the_ceiling` | — |
| Nothing is rented or created without the price and a `y` (`serve`, `volume up`) | [D35](decisions.md#d35--the-price-first-yn---yes-skips-it) | `test_nothing_is_rented_unless_the_operator_says_y`, `test_no_is_the_default`, `test_an_interrupt_at_the_price_creates_nothing` | — |
| Every input that shapes a pod is pinned | [D11](decisions.md#d11--spec-from-gpunittoml-strict-keys-a-digest-a-required-ceiling-checked-ports), [D40](decisions.md#d40--the-serve-image-vllm-by-digest-the-launcher-turns-logging-and-telemetry-off) | `test_an_image_without_a_digest_is_refused`, `test_a_moving_revision_is_refused_naming_the_row`, `test_the_image_is_built_from_pinned_inputs`, `test_each_action_is_pinned_by_commit` | breached: `gpunit/serve/table.py::_args` matches exact launcher flags; an abbreviation repins a user row (`0015·F23`) |
| Secure Cloud, port 22 alone | [D19](decisions.md#d19--placement-the-catalogue-floor-one-create-per-card-a-400-moves-on-the-rest-is-lost) | `test_the_create_is_secure_and_exposes_22_only` | — |
| Every amount is the provider's; an unreadable billing is an error | [D44](decisions.md#d44--spend-whole-utc-days-the-providers-amounts-one-rounding) | `test_the_total_is_the_providers_rounded_once`, `test_an_unreadable_billing_is_an_error_not_zeros` | — |
| The ledger never blocks a session | [D17](decisions.md#d17--the-ledger-best-effort-to-write-refuses-to-read-spend-joins-on-it) | `test_an_unwritable_ledger_blocks_nothing`, `test_no_home_blocks_nothing` | — |

### The window volume

| rule | from | held by | breach |
|---|---|---|---|
| The sweep runs first; a forgotten volume ends at the next command | [D43](decisions.md#d43--every-session-mounts-the-window-the-sweep-runs-first) | `test_an_overdue_volume_is_deleted_first`, `test_serve_sweeps_an_overdue_volume_before_the_price`, `test_down_deletes_an_overdue_volume_after_its_pods` | — |
| No session outlives its volume | [D43](decisions.md#d43--every-session-mounts-the-window-the-sweep-runs-first), [D41](decisions.md#d41--volume-up-and-down-the-sweep-asks-a-person-at-a-terminal) | `test_a_session_past_the_volumes_end_refuses`, `test_up_again_never_pulls_the_end_in` | — |
| An unrecorded volume is deleted only on a person's `y` at a terminal | [D41](decisions.md#d41--volume-up-and-down-the-sweep-asks-a-person-at-a-terminal) | `test_the_sweep_asks_before_each_delete`, `test_the_sweep_asks_only_a_terminal`, `test_ctrl_c_ends_the_sweep` | — |

### Input and output

| rule | from | held by | breach |
|---|---|---|---|
| No request before the spec, the record and the tools are checked | [D11](decisions.md#d11--spec-from-gpunittoml-strict-keys-a-digest-a-required-ceiling-checked-ports), [D24](decisions.md#d24--gpunits-ssh-is-its-own-the-tools-checked-before-any-request) | `NO_REQUESTS` in `tests/helpers.py`, `test_a_busy_port_refuses_before_any_request`, `test_no_ssh_keygen_refuses_before_any_request` | — |
| A spec or table fault refuses before any request, naming the field | [D11](decisions.md#d11--spec-from-gpunittoml-strict-keys-a-digest-a-required-ceiling-checked-ports), [D34](decisions.md#d34--a-model-is-a-row-the-bundled-table-and-one-user-file) | `test_a_missing_required_field_is_named`, `test_an_unknown_key_is_refused_naming_the_nearest`, `test_a_faulty_table_is_refused_naming_the_field` | — |
| A refusal is one stamped stderr line; `refused:` opens it | [D4](decisions.md#d4--gpunits-lines-utc-stamped-to-stderr-or-a-sink-refused-opens-a-refusal-a-dead-pipe-swallowed-sysexit-in-cli-alone) | `test_a_refusal_is_one_stamped_stderr_line`; review for the other sites | — |
| stdout belongs to the command; gpunit's lines go to stderr | [D4](decisions.md#d4--gpunits-lines-utc-stamped-to-stderr-or-a-sink-refused-opens-a-refusal-a-dead-pipe-swallowed-sysexit-in-cli-alone) | `test_stdout_carries_only_the_commands_output`, `test_the_lines_open_with_the_utc_time` | — |

### The code

| rule | from | held by | breach |
|---|---|---|---|
| The standard library alone: the package, `boot.py`, `serve/launch.py` | [D1](decisions.md#d1--a-flat-stdlib-package-python-311-no-runtime-dependency), [D45](decisions.md#d45--bootpy-one-stdlib-file-for-python-310-no-gpunit-import) | `architecture:layers:stdlib-only`, `test_boot_imports_the_stdlib_alone` | — |
| `sys.exit` in `cli` alone | [D4](decisions.md#d4--gpunits-lines-utc-stamped-to-stderr-or-a-sink-refused-opens-a-refusal-a-dead-pipe-swallowed-sysexit-in-cli-alone) | `architecture:layers:exit-in-cli` | — |
| Imports point down the layers | [D49](decisions.md#d49--the-layers-held-by-teststest_layerspy) | `architecture:layers:hold` | — |
| The seam names no provider noun | [D2](decisions.md#d2--a-provider-protocol-its-nouns-not-runpods) | nothing | breached: `gpunit/lifecycle.py::_delete_pods` compares HTTP codes (`0015·F3`); `gpunit/lifecycle.py::DEAD` and `gpunit/volume.py::STOCK` are RunPod's words (`0015·F5`); `gpunit/library.py::session` builds `RunPod` (`0015·F2`) |
| Every scenario has a test, every test a key | [D5](decisions.md#d5--the-gate-fakes-every-provider-answer-bootpy-at-100-) | `--strict-markers` in `pyproject.toml`; the one-to-one, review | — |

### The process

| rule | from | held by | breach |
|---|---|---|---|
| An archived change is a record | [D7](decisions.md#d7--an-archived-change-is-a-record-a-card-against-it-closes-wont-fix) | review | — |
| A patch adds no verb, key or exit code | [D8](decisions.md#d8--a-patch-closes-cards-it-adds-no-verb-gpunittoml-key-or-exit-code) | review | — |
| A trust-boundary change edits the threat model | [D9](decisions.md#d9--the-threat-model-lives-in-docs-and-moves-with-every-trust-boundary-change) | review | — |
| The live proofs run by hand, outside CI; the price prints first | [D6](decisions.md#d6--the-metered-proofs-run-by-hand-the-price-first-their-tails-committed-a-boot-change-rebuilds-the-images) | review | — |
| A refactor changes no scenario | [D51](decisions.md#d51--a-refactor-changes-no-scenario-message-or-exit-code) | the unchanged tests; review | — |
