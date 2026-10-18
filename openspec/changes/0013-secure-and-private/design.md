# Design — 0013 secure and private

How each gap of the threat model closes, how `datacenters` places pods and volumes, what the probe measures, and how
the threat model enters the repo. **Verdict: feasible** — each fix sits at a line the threat model names, and RunPod's
create takes a list of data centres.

## Context

See [proposal](proposal.md) — *Why*. The input is the threat-model draft, `threat-model.md` beside the grilling's
brief in the operator's notebook; its ids are `G…` (gaps) and `T…` (threats). What holds at the cut, `main` at
`f3262de` (`v0.8.0`):

- **G2, T21:** `_command` builds the command's environment as `os.environ | {…}` (`gpunit/run.py:52`).
- **G3, T9:** `_Tunnel._watch` reopens a dead tunnel with backoff (`gpunit/library.py:193-205`); the busy-port probe
  reads `127.0.0.1` alone, once, before `up` (`gpunit/library.py:265-274`, called at `:90`); the tunnel opens after
  `up`, minutes later (`:113-114`). `ssh` exits on a forward it cannot bind (`ExitOnForwardFailure`, `:252`), so a
  taken port shows as a tunnel that dies at once, as a dead one does. *Corrected at the converge (security S1):*
  `-L<local>:localhost:<remote>` binds `127.0.0.1` and `::1`, and OpenSSH counts the forward as set up when either
  binds, so a port taken on one family alone does not end `ssh`; [D5](#d5) binds each family as its own forward.
- **G7, T25, T26:** `_env` refuses `GPUNIT_*` names only (`gpunit/spec.py:184-190`).
- **G8, T34:** `create` sends `dataCenterIds` only with a volume (`gpunit/runpod.py:130-142`); `volume up`'s choice
  reads stock with no filter (`gpunit/volume.py:187-209`); `PodInfo` holds no data centre (`gpunit/provider.py:83-88`).
- **G9, T30:** the rows' `args` set no request-logging flag (`gpunit/serve/models.toml:8-9`, `:18-19`).
- **G11, T39:** pod-log lines print raw: `loading: …` (`gpunit/serve/session.py:229`) and `pod: …` (`:267`).
- **G13, T17:** `_mkdir` makes `.gpunit/` at `0700` but leaves a found one as it is (`gpunit/state.py:143-144`).
- **The cards:** each `0012·R3`–`R9` card's *Still true?* holds at `f3262de`, read against the archived paths.

**RunPod's create, read at the cut** ([create a pod](https://docs.runpod.io/api-reference-v2/pods/create-a-pod)):

> `dataCenterIds: type string[]; description Preferred data centers for placement. Omit or pass an empty array to let
> the scheduler choose.`

> `400` … "this GPU and data center combination could not be placed. | Try your next candidate."

The 201 and `GET /v2/pods/{id}` bodies carry `dataCenterId: type string | null` — "Data center where the pod is
running (assigned by scheduler)". *Preferred* leaves open whether the list binds: [D8](#d8) checks where the pod
landed.

**vLLM `v0.31.0`, read at the cut** — the serve image's base is `vllm/vllm-openai:v0.31.0` (`serve/Dockerfile:3`).
`vllm/engine/arg_utils.py` at the tag:

```
3128:    enable_log_requests: bool = False
3141:            "--enable-log-requests",
3142:            action=argparse.BooleanOptionalAction,
3143:            default=AsyncEngineArgs.enable_log_requests,
3144:            help="Enable logging request information, dependent on log level:\n"
3145:            "- INFO: Request ID, parameters and LoRA request.\n"
3146:            "- DEBUG: Prompt inputs (e.g: text, token IDs).\n"
```

`vllm/entrypoints/launchers/cli_args.py` at the tag: `enable_log_outputs: bool = False` — "log model outputs
(generations). Requires `--enable-log-requests`". So request logging is off by default at `v0.31.0`;
`BooleanOptionalAction` makes `--no-enable-log-requests` the explicit off. The tag has no `--disable-log-requests`.

| measure | value | command |
|---|---|---|
| threats in the draft | 54 | `grep -c -E '^\| T[0-9]+ ' threat-model.md` |
| its rows `gap` | 9: T9, T21, T22, T24, T26, T30, T34, T39, T54 | `grep -E '^\| T[0-9]+ ' threat-model.md \| grep -c '\| gap \|'` |
| the draft's own *Counts* line | `mitigated 23 · partly 11 · gap 10 · accepted 10`, stale: T4 is `mitigated` | `grep -n '^Counts' threat-model.md` |

## Goals / Non-Goals

**Goals:** each gap Q6 and Q7 settle closed in code with a scenario; where data lands, written down; RunPod's
undocumented powers measured once; the threat model versioned with the code.

**Non-Goals:** a `compliance` or country key; an encrypted volume; a new host-key protocol; a change to `boot.py`'s
behaviour.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | `run`'s command environment drops `RUNPOD_API_KEY` | the command never needs the account key (T21) | dropping every `RUNPOD_*` |
| [D2](#d2) | `[env]` refuses `RUNPOD_*` names; values pass as written | a consumer's `RUNPOD_API_KEY` would land the account key in pod env (T26) | parsing secret references |
| [D3](#d3) | every `.gpunit/` write first sets the directory to `0700` | a found directory kept a loose mode (T17) | a check that refuses |
| [D4](#d4) | `log.clean` removes C0, DEL and C1 from each printed pod-log line; `pod.log` stays as read | a command's output steers the terminal (T39) | escaping as `\x1b` |
| [D5](#d5) | a **taken port** — one answering on `127.0.0.1` or `::1` while the tunnel does not hold it — refuses: before the tunnel opens, after it exits, before a reopen | a reopen sends the traffic to the squatter (T9) | refusing every tunnel exit |
| [D6](#d6) | the watcher ends the block through the session's signal handler, which raises `Refused` | a thread cannot raise in the main one; a signal wakes a blocked `wait` | `_thread.interrupt_main` |
| [D7](#d7) | `datacenters`: an optional non-empty list of strings; a `volume_datacenter` outside it is refused at load | one allow-list for pods and volumes (Q7) | a check at `volume up` alone |
| [D8](#d8) | the create sends `datacenters`; a mounted volume outside it refuses; the wait reads the pod's `dataCenterId` and tears down one outside | RunPod calls the list *preferred* | trusting the list |
| [D9](#d9) | `volume up`'s stock choice reads only data centres in `datacenters` | a window volume pins every pod of the window | — |
| [D10](#d10) | `--no-enable-log-requests` in each row's `args` | the off is explicit, whatever a later vLLM defaults to (T30) | relying on the default |
| [D11](#d11) | `0012·R5`, `R6`'s code half, `R8`, `R9` fixed in live text | Q13 | — |
| [D12](#d12) | `0012·R3`, `R4`, `R7` and `R6`'s CHANGELOG half close won't-fix | they name the released `[0.8.0]` entry or the archived design | editing released text |
| [D13](#d13) | README's *Security and privacy*, its `datacenters` line and its `[env]` comment | the operator can only protect what is named (Q8) | a separate page |
| [D14](#d14) | `docs/threat-model.md` from the draft at `v0.9`'s state; `CLAUDE.md`'s trust-boundary rule | versioned with the code, kept current (Q4, Q11) | the vault alone |
| [D15](#d15) | the probe: G6 on a restricted key with `make live` and `make live-volume`; G5 and G12 from a pod's shell | RunPod documents none of them (Q9) | a scripted probe |

### D1

`_command` (`gpunit/run.py:52`):
`env = os.environ | {…}` → `env = {k: v for k, v in os.environ.items() if k != "RUNPOD_API_KEY"} | {…}`.

- **The library is unchanged:** it starts no command.
- **The provider still reads the key** from `os.environ` (`gpunit/runpod.py:80-83`); `run:handover:no-account-key`
  checks the command's environment and the requests.
- **Only the account key:** `RUNPOD_*` names a consumer sets on the laptop for its own use pass.

### D2

`_env` (`gpunit/spec.py:184-190`) refuses a name starting `RUNPOD_` as it refuses `GPUNIT_`:
`{path}: env {key!r} is RunPod's; [env] may name no RUNPOD_*`. A value is never read: `HF_TOKEN =
"{{ RUNPOD_SECRET_hf_token }}"` reaches the create as written. Whether RunPod substitutes it through v2's create is
not proven here ([proposal](proposal.md) — *Not in this change*); README says so.

### D3

`State._mkdir` (`gpunit/state.py:143-144`): after `self.dir.mkdir(mode=0o700, exist_ok=True)`, `self.dir.chmod(0o700)`.
Every write already goes through `_mkdir` or `_replace`, which calls it.

### D4

`gpunit/log.py` gains `clean(text: str) -> str`: it deletes each character in U+0000–U+001F and U+007F–U+009F.

```
"\x1b]0;owned\x07loading\x1b[2J 50%"  →  "]0;ownedloading[2J 50%"
```

- **The sites:** `log.say(f"loading: {lines[-1]}")` → `log.say(f"loading: {log.clean(lines[-1])}")`
  (`gpunit/serve/session.py:229`); `log.say(f"pod: {line}")` → `log.say(f"pod: {log.clean(line)}")` (`:267`).
- **`pod.log` keeps the line as read:** it is evidence, at `0600`.
- **The host-key parse is untouched:** it matches whole lines (`gpunit/provider.py:32-45`), and a forged line gains
  nothing from a control character.

### D5

**A taken port** is a spec'd local port that accepts a connection on `127.0.0.1` or on `::1` while gpunit's tunnel
does not hold it. One helper, `_taken(spec) -> int | None` in `gpunit/library.py`, returns the first; a connect to
`::1` that fails, as on a host without IPv6, reads as free.

```
_open:  _taken → refuse (busy, as now)  ── up (minutes) ──  _taken → refuse  ── _Tunnel opens
_watch: child exits ─▶ _taken? ── yes ─▶ refuse, stop watching
                            └── no ──▶ backoff wait ─▶ _taken? ── yes ─▶ refuse
                                                         └── no ──▶ reopen
```

- **Before `up`:** `_refuse_busy_ports` (`gpunit/library.py:265-274`) uses `_taken`; its message is unchanged:
  `local port N already answers; free it, or set its local side`.
- **After `up`, before the tunnel** (`:113-114`): `_taken` again; a taken port refuses
  `local port N was taken while the pod came up; the session ends`. The refusal is inside the `try`, so the
  teardown runs.
- **In `_watch`** (`:193-205`): on the child's exit, and again when a reopen is due, `_taken`; a taken port calls the
  refusal of [D6](#d6) with `local port N is taken by another process; the tunnel cannot hold it`, and the watcher
  returns. A free port keeps today's backoff, its log line and its waits.
- **One forward per loopback family** (converge, security S1): `_tunnel_argv` passes
  `-L127.0.0.1:<local>:localhost:<remote>`, and `-L[::1]:<local>:localhost:<remote>` when `::1` binds on the host.
  A family another process holds then fails its own forward, `ExitOnForwardFailure` ends `ssh`, and the watcher's
  `_taken` refuses. Checked by hand against OpenSSH 10.3p1: with `127.0.0.1` or `::1` held, `localhost` stays up on
  the other family; the per-family forwards exit `255`, `Could not request local forwarding`.
- **`serve`** picks its port free on `127.0.0.1` (`gpunit/serve/session.py:137-141`); `_open`'s probe now reads `::1`
  too.

### D6

The watcher thread cannot raise in the main thread, and the block may sit in a blocking call, as `run`'s
`child.wait()`.

- **`_Signals.refuse(text)`** stores `text`, then `signal.pthread_kill(threading.main_thread().ident, signal.SIGINT)`.
- **`_Signals._handle`**, when a text is stored and it has not fired: clears the text, then `log.refuse(text)`, which
  says the line and raises `log.Refusal` (`gpunit.Refused`) in the main thread. It does not set `_fired`, so a block
  that swallows the `Refused` still ends on a later signal (converge, security S2). With no text, `Interrupted` as
  now.
- **`_Tunnel(argv, spec, refuse)`** takes the callable; `_open` passes `signals.refuse`.
- **`run._command`:** `except library.Interrupted:` → `except (library.Interrupted, log.Refusal):` — it ends the child
  before re-raising. `outcome` already maps `log.Refusal` to `1`.
- **The teardown is shielded as now:** `signals.shield()` comes before `tunnel.stop()`.

### D7

`gpunit/spec.py`: `"datacenters": (list,)` in `_OPTIONAL` (`:28-39`); `Spec.datacenters: tuple[str, ...] = ()`;
loaded by the check `_gpus` makes, naming `datacenters`: `'datacenters' must be a non-empty list of strings`. After
`_volume_ceiling`, a `volume_datacenter` not in a set `datacenters` refuses
`{path}: 'volume_datacenter' {dc!r} is not in 'datacenters'`.

```toml
datacenters = ["EU-RO-1", "EU-SE-1"]   # pods and window volumes go nowhere else
```

### D8

```
up:  volume read (lifecycle.py:92-96) ── dc ∉ datacenters ─▶ refuse, no create
     create ── no volume: "dataCenterIds": list(spec.datacenters) · volume: [the volume's dc], as now
     _wait.mapped ── info.datacenter ∉ datacenters ─▶ tear down, exit 1
                  └─ None ─▶ not yet          └─ ∈ ─▶ up, as now
```

- **The volume read:** `up` keeps `provider.volume(spec.volume)`'s answer (`gpunit/lifecycle.py:92-96`); its
  `datacenter` outside a set `spec.datacenters` refuses
  `volume <id> is in <dc>, outside datacenters <A, B>`. A window volume is read there too: `_in_window` sets
  `spec.volume`.
- **The create** (`gpunit/runpod.py:130-142`): with no volume and a set `spec.datacenters`,
  `placement = {"dataCenterIds": list(spec.datacenters)}`. Without `datacenters`, the body is today's.
- **The pod's data centre:** `PodInfo.datacenter: str | None = None` (`gpunit/provider.py:83-88`), read by
  `RunPod.get` from `body.get("dataCenterId") or None` (`gpunit/runpod.py:164-177`).
- **The wait** (`gpunit/lifecycle.py:356-381`): with `spec.datacenters` set, `mapped` returns the pod only when its
  `datacenter` is in it; one outside tears down with `pod <id> was placed in <dc>, outside datacenters <A, B>`; `None`
  is not yet, so the deadline bounds a pod that never names one.

### D9

`_datacenter` (`gpunit/volume.py:187-209`): `placed` keeps a pair only when `spec.datacenters` is empty or holds its
data centre. The refusal gains the list when set:
`no card of gpus is in stock in a data centre with standard volumes within datacenters EU-SE-1: <cards>`. A given
`volume_datacenter` is already inside the list ([D7](#d7)).

### D10

`gpunit/serve/models.toml`: each row's `args` gains `"--no-enable-log-requests"` at its end. The image is not rebuilt:
`args` reach `serve/launch.py` as `SERVE_ARGS` in the pod's environment (`gpunit/serve/table.py:69`).

- **`tests/test_serve_table.py:110-111`** asserts `qwen3-4b`'s `SERVE_ARGS` word for word; it gains the flag.
- **A new test** binds `serve:table:request-logging-off` over every row of the bundled table.

### D11

- **`0012·R5`:** `test_no_ca_store_refuses_before_the_arm` and `test_a_ca_directory_alone_is_a_store`
  (`tests/test_boot_steps.py:198-200`, `:221-222`) move from `boot:refuse:no-sshd` to `boot:refuse:no-ca-store`,
  added by [the boot delta](specs/boot/spec.md).
- **`0012·R6`, its code half:** the comment at `boot/boot.py:105`, `# The cause, a missing CA store say, holds no key.`
  → `# The cause, a store that does not trust RunPod's certificate say, holds no key.`;
  `test_no_ca_store_names_the_cause` → `test_an_untrusted_certificate_names_the_cause`, its comment at
  `tests/test_boot_steps.py:575` → `# What urllib raises when the store lacks the root RunPod's certificate needs.`
- **`0012·R8`:** README's `make live-dead` paragraph (`README.md:323-324`) gains: "then deletes what `up` left; a
  failed `gpunit down` fails it. In a checkout that records a pod it exits `1` and rents nothing."
- **`0012·R9`:** `test_dead_leaves_a_recorded_pod_alone` (`tests/test_live.py:112-114`) moves to
  `session:wait:dead-proof-spares-a-record`, added by [the session delta](specs/session/spec.md).

### D12

Each names text an archived change or a released entry records; an archived change records what held then (`0008·R5`,
`0012` D11).

- **`0012·R3`:** `openspec/changes/archive/0012-boot-in-python/design.md:281` and `CHANGELOG.md:33`, in `[0.8.0]`. Its
  substance, scripts no real pod ran, is answered by [D15](#d15): `make live` and `make live-volume` run `live/*.py`
  at this change's head.
- **`0012·R4`:** the `[0.8.0]` *Fixed* ids.
- **`0012·R7`:** `CHANGELOG.md:64`, in `[0.8.0]`.
- **`0012·R6`'s CHANGELOG half:** `CHANGELOG.md:48`, in `[0.8.0]`.
- **They close won't-fix**, listed in the proposal's `backlog:`. No task edits them.

### D13

README:

- **The `gpunit.toml` example** (`README.md:20-40`): a `datacenters = ["EU-RO-1"]` line under `# optional`, its
  comment `# pods and window volumes go nowhere else`; the `[env]` comment `GPUNIT_* names are gpunit's, and refused
  here` → `GPUNIT_* and RUNPOD_* names are refused here`.
- **Step 3** says `run`'s command gets no `RUNPOD_API_KEY`.
- **A new `## Security and privacy`**, before `## The verbs`, linking `docs/threat-model.md`:
  - `### Where your data lands` (G10): the pod's env, API-readable until `down`; the pod's log, its retention
    undocumented, and vLLM's request logging off; the window volume, unencrypted and S3-reachable until its sweep;
    on the laptop `pod.log`, the ledger and `.gpunit/`. Keep private data off stdout and off the volume.
  - `### Secrets`: `[env]` is plain pod env; put a token in a RunPod secret and name it,
    `HF_TOKEN = "{{ RUNPOD_SECRET_hf_token }}"`, its substitution through v2's create not yet proven.
  - `### The account key`: the calls gpunit makes — the catalogue, pods (create, read, list, logs, delete), network
    volumes (create, read, list, delete), billing (read); the minimum a restricted key needs, measured by
    [D15](#d15).
  - `### Accepted risks`: RunPod's hosts can read a pod's memory and disk (Q2); every local user reaches
    `GPUNIT_PORT_*` (G4); the session key sits unencrypted in `.gpunit/`, for one session (G16).

### D14

- **`docs/threat-model.md`:** the draft at [the draft](threat-model-draft.md) in this change's directory, its
  vault frontmatter dropped, its title `# gpunit — threat model`, its code citations re-read at this change's head,
  and each row brought to `v0.9`: T17, T21, T26, T30, T34, T39 `mitigated`; T9 `partly`, the seconds between `ssh`'s
  start and its bind; T36, T37 `accepted`; T22, T24, T54 stay `gap` until [D15](#d15). Each G row names its outcome.
  Its *Counts* line is recounted from the table. It ends with `## 7. The probe`, which [D15](#d15) fills.
- **`CLAUDE.md`:** the layout names `docs/threat-model.md`; a new invariant: **A change that touches a trust boundary
  updates `docs/threat-model.md`**: a new flow, secret, file mode, network call or log line.

### D15

By hand, metered, about $0.05: a `live` pod and a `live-probe` pod for a few minutes, and the `make live-volume`
window. Each result is a
line under `## 7. The probe` in `docs/threat-model.md`, `- **G<n> measured:** <what held>`, and the status of
T22, T24 or T54 follows it.

- **G6 — the restricted key.** In the console, make an API key with the narrowest permissions it offers. With it as
  `RUNPOD_API_KEY`, run `make live`, `make live-volume` and `uv run gpunit spend --days 1`. On a 401 or 403, widen one
  permission and run again. The last set that passes is the minimum: README's `### The account key` gains
  `- **Measured minimum:** <the console's settings>`. The tails go to `live/last_run.txt`.
- **G5 — the pod-scoped key.** A scratch checkout holds the `live-probe` pod; the `live` pod's shell reads its own
  key and tries it. The laptop block:

```
REPO=$PWD; mkdir -p /tmp/gpunit-probe
sed 's/^project = "live"$/project = "live-probe"/' live/gpunit.toml > /tmp/gpunit-probe/gpunit.toml
(cd /tmp/gpunit-probe && uv run --project "$REPO" gpunit up)
python3 -c 'import json; print(json.load(open("/tmp/gpunit-probe/.gpunit/pod"))["id"])'   # <other>
uv run gpunit up --spec live/gpunit.toml && uv run gpunit ssh --spec live/gpunit.toml
```

The pod block, on the `live` pod's shell, `<other>` replaced:

```
envs() { for p in /proc/[0-9]*; do tr '\0' '\n' < "$p/environ" 2>/dev/null; done; }
export K=$(envs | sed -n 's/^RUNPOD_API_KEY=//p' | head -n 1)
OWN=$(envs | sed -n 's/^RUNPOD_POD_ID=//p' | head -n 1)
for path in pods "pods/$OWN" "pods/<other>" network-volumes \
    "billing/pods?bucketSize=day&startTime=2026-10-01T00:00:00Z&endTime=2026-10-02T00:00:00Z"; do
  python3 -c 'import os, sys, urllib.error, urllib.request as u
r = u.Request("https://api.runpod.io/v2/" + sys.argv[1], headers={"Authorization": "Bearer " + os.environ["K"], "User-Agent": "gpunit-probe"})
try:
    with u.urlopen(r, timeout=30) as a: print(sys.argv[1], a.status, a.read(200))
except urllib.error.HTTPError as e: print(sys.argv[1], e.code)' "$path"
done
cat /root/.ssh/authorized_keys          # G12
```

- **G12 — account SSH keys.** With an SSH key registered in the console's account settings, the pod's
  `authorized_keys`, read above five minutes after `up`, is compared with the laptop's `cat .gpunit/key.pub`. Then
  the pod's `ssh.proxy`, from
  `printf 'Authorization: Bearer %s\nUser-Agent: gpunit-probe\n' "$RUNPOD_API_KEY" | curl -s -H @- https://api.runpod.io/v2/pods/<id>`,
  is tried with the account key: `ssh -o IdentitiesOnly=yes -i <the account key's private file> <ssh.proxy> true; echo $?`.
- **The end:** `uv run gpunit down --spec live/gpunit.toml`, then
  `(cd /tmp/gpunit-probe && uv run --project "$REPO" gpunit down)`; the console shows no pod and no `gpunit-` volume;
  the restricted key is deleted in the console.

## Dependencies

None.

## Risks / Trade-offs

- **A squatter can bind in the seconds between `ssh`'s start and its bind** → [D5](#d5) narrows the window from
  minutes to seconds: the squatter's family fails its forward, and the watcher refuses within a poll of `ssh`'s
  exit; `serve`'s first poll may reach it in that window. T9 stays `partly` in the threat model.
- **`pthread_kill` with `SIGINT` from the watcher** → the handler is gpunit's while the session is open, and the
  teardown ignores signals; a library consumer sees `Refused`, as for any refusal.
- **`dataCenterIds` may only order RunPod's choice** → [D8](#d8)'s wait check tears down a pod outside the list; it
  bills until its delete.
- **A pod whose read never names a data centre** waits to the deadline and tears down: `datacenters` set means no
  pod is up unplaced.
- **`--no-enable-log-requests` unproven on a pod here** → the flag is read from `v0.31.0`'s source; `make live-serve`
  runs at the next serve change.
- **A `run` command that read `RUNPOD_API_KEY` breaks** → the CHANGELOG names it; such a command reads the key from
  its own source.

## Migration Plan

A consumer whose `run` command calls RunPod sets its own variable for it, outside `RUNPOD_API_KEY`'s name. An
`[env]` holding `RUNPOD_*` moves the value to a RunPod secret. `datacenters` is opt-in. Rollback is `v0.8.0`.

## Verdict

Feasible: every fix but placement is a line or two at a cited site; placement adds a list key, one create field and
one check in the wait. The probe is the only metered step, and the only one RunPod's docs could not replace.
