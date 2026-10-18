# gpunit — threat model

What gpunit protects, who it is protected from, and what holds at `v0.9`; code cited as `path:line`, RunPod cited by doc URL, anything unproven marked *not verified* or *undocumented*.

**The frame (settled):** RunPod is trusted with the compute on Secure Cloud only, and its host operators **can read pod memory and disk**. Its ToS forbids them to inspect it, but no confidential computing is documented. Untrusted: the network path, a command's output, other local users on the laptop, a leaked laptop key, a consumer's own command beyond the pod-scoped key, and the supply chain (images, `boot.py`, Python deps, git tags). **"Private" for gpunit:** gpunit puts nothing of the consumer's on RunPod beyond the session's need and for no longer than the session, documents where data can land (pod log, window volume, pod env) and offers placement controls. Keeping its own data out of logs and off volumes is the consumer's job.

A change that touches a trust boundary updates this file: a new flow, secret, file mode, network call or log line.

## 1. Assets

| id | asset | where it lives | who must not get it |
|---|---|---|---|
| A1 | the account API key (laptop's `RUNPOD_API_KEY`) | the laptop process env, read at `gpunit/runpod.py:80-83`; it goes only in a request header (`gpunit/runpod.py:360`) | the network, other local users, the consumer's command, the pod |
| A2 | the pod-scoped `RUNPOD_API_KEY` | the pod env, injected by RunPod ([env vars](https://docs.runpod.io/pods/templates/environment-variables#runpod-provided-variables)); boot's process env; kept out of the command's env (`boot/boot.py:40`, `:232`) | the command, beyond the stop it serves; the network |
| A3 | the session's SSH private key | `.gpunit/key`, or `~/.local/state/gpunit/serve/<model>/.gpunit/key` for `serve` (`gpunit/state.py:57`, `:113-136`; `gpunit/serve/session.py:33-38`) | other local users, backups and sync folders, git |
| A4 | the pod's host key and its fingerprint (integrity) | `tempfile.mkdtemp` on the pod (`boot/boot.py:192-198`); the fingerprint line in the container log (`boot/boot.py:269`) | anyone positioned to stand in for the pod (network MITM, a forged log line) |
| A5 | the session nonce | the pod env as `GPUNIT_NONCE` (`gpunit/runpod.py:128`); kept out of the command's env (`boot/boot.py:40`) | the command, which could otherwise forge the key line |
| A6 | the vLLM key (`serve`) | the pod env as `VLLM_API_KEY` (`gpunit/serve/table.py:70`); laptop memory; `--api` stdout (`gpunit/serve/session.py:245-246`) | other local users; anyone beyond the session's client |
| A7 | the consumer's payload: photographs of real people (isekai), prompts and answers (Hermes, chat), outputs | the laptop, the tunnel, pod memory and container disk, possibly the window volume | the network, other local users, RunPod beyond the Secure Cloud host, logs that outlive the session |
| A8 | the consumer's `[env]` values | `gpunit.toml`, the pod env (`gpunit/runpod.py:124-129`) | anyone reading pod env through the API or console |
| A9 | the container log | RunPod, readable through `GET /v2/pods/{id}/logs` ([stream pod logs](https://docs.runpod.io/api-reference-v2/pods/stream-pod-logs)); the laptop copy `pod.log`, mode 0600 (`gpunit/serve/session.py:196`) | other account-key holders and other local users, for longer than the session |
| A10 | the window volume's contents (weights; whatever the command writes) | a RunPod network volume at `/runpod-volume` (`gpunit/runpod.py:39`, `:139-144`) | S3-key holders; anyone after the window ends |
| A11 | gpunit's local records: the ledger and `.gpunit/pod` | `~/.local/state/gpunit/ledger.jsonl` (`gpunit/ledger.py:47-49`); `.gpunit/` (`gpunit/state.py:51-60`) | other local users; they hold metadata only (ids, project, image, times; `spend:ledger:holds-nothing-else`) |
| A12 | money: the account balance | the RunPod account | a runaway pod or volume; a hostile command or key |
| A13 | the integrity of what runs: images, `boot.py`, weights, the gpunit package | registries (ghcr, the consumer's), GitHub, Hugging Face | a tampering supply chain |

## 2. Actors and trust boundaries

```
   laptop — the operator's uid                                       RunPod — trusted (Secure Cloud)
 ┌──────────────────────────────────────────────┐   B1: TLS, key in  ┌───────────────────────────────────┐
 │ gpunit CLI / library        A1 in env        │   a header         │ RunPod API v2                     │
 │ .gpunit/{key,pod,known_hosts}   A3, A11      │──── F1, F8 ──────▶│  pod env: A2 A5 A6 A8 (readable)  │
 │ ~/.local/state/gpunit/{ledger,serve/*}       │◀─── F4: log SSE ───│  container log: A9 (readable)     │
 │                                              │                    └───────┬──────────────────▲───────┘
 │ consumer command / Hermes (serve --api, F11) │                            │ F2: place, pull  │ F7: stop,
 │   └─▶ 127.0.0.1:<local> ─┐                   │                            ▼    by digest     │ A2 header
 │ other local users ─ ─ ─ ─┤  B3: loopback     │   B2: SSH, public  ┌───────────────────────────────────┐
 │                  ssh -N -L (tunnel, F6) ═════│════ host:port ════▶│ pod — root in a container         │
 └──────────────────────────────────────────────┘   F5: keyscan, key │  boot.py · sshd · watchdog        │
                                                                     │  B4 ─ the command / vLLM 127.0.0.1│
   B5: supply chain ─▶ images (ghcr, consumer's) · boot.py           │  /runpod-volume ◀── window volume │
       (GitHub tag) · weights (HF, F3) · gpunit (git tag)            │     A10, F9 (also S3 API) ──▶ B6  │
                                                                     └───────────────────────────────────┘
```

Boundaries: **B1** laptop ↔ RunPod API over the internet. **B2** laptop ↔ pod sshd over the internet. **B3** the operator's uid ↔ other local users, through loopback ports and files. **B4** boot ↔ the command; a weak boundary, since both run as root in one container. **B5** the supply chain ↔ the pod and the laptop. **B6** the session ↔ the rest of the account: other keys, team members, S3 keys.

| actor | trusted? | why |
|---|---|---|
| the operator (the human at the laptop) | trusted | owns the account key and the consumer's data |
| gpunit's own code | trusted | subject to B5 for how it is installed (T15) |
| RunPod, platform and Secure Cloud host operators | trusted with the compute | the settled frame. Hosts can read memory and disk; the ToS forbids inspection ([host access](https://docs.runpod.io/references/security-and-compliance#host-access-policies)); no confidential computing is documented |
| Community Cloud hosts | untrusted | "peer-to-peer providers" ([choose a pod](https://docs.runpod.io/pods/choose-a-pod#secure-cloud-vs-community-cloud)); gpunit never creates there (`gpunit/runpod.py:151`) |
| other RunPod tenants | untrusted | RunPod isolates them in containers ([multi-tenant isolation](https://docs.runpod.io/references/security-and-compliance#multi-tenant-isolation)) |
| the network path (Wi-Fi, ISP, DNS, the internet) | untrusted | B1 and B2 cross it |
| other local users on the laptop | untrusted | they share loopback, and `/tmp`-style exposure if modes are loose |
| whoever holds a leaked laptop key (A3) | untrusted | through a backup, a sync folder or a commit |
| the consumer's command (laptop and pod) | trusted with its own data only | untrusted beyond the pod-scoped key; on the pod it runs as root beside boot (`boot/boot.py:229-244`) |
| the agent (Hermes) on `serve --api` | trusted with the vLLM key it is handed | it reads the key from stdout (`gpunit/serve/session.py:246`) |
| a command's output (the container log) | untrusted | it feeds the host-key parse (`gpunit/provider.py:32-45`) and the operator's terminal, cleaned (`gpunit/serve/session.py:229`, `:267`) |
| the supply chain: registries, GitHub tags, Hugging Face, apt | untrusted | integrity comes from pins alone (T11-T16) |
| other holders of the account (team roles, other API keys, S3 keys) | outside gpunit's control | they can read pod env, logs and volumes ([roles](https://docs.runpod.io/accounts-billing/manage-accounts), [S3 keys](https://docs.runpod.io/get-started/credentials#s3-api-keys)) |

## 3. Data flows

1. **F1, create (laptop → API, B1).** The image digest, cards, disk, `cloud: SECURE`, `ports: ["22/tcp"]`, `dataCenterIds` from `datacenters` when set, and env holding the `[env]` values plus `PUBLIC_KEY`, `GPUNIT_CEILING` and `GPUNIT_NONCE` (`gpunit/runpod.py:115-164`, `:131-132`). TLS to a hard-coded host (`gpunit/runpod.py:30`); A1 travels in a header, and no redirect is followed (`gpunit/runpod.py:56-69`, `:84`). The env is stored by RunPod and readable back (`env` is in `GET /v2/pods/{id}`, [get a pod](https://docs.runpod.io/api-reference-v2/pods/get-a-pod)).
2. **F2, the image pull (registry → host, B5).** By `@sha256` digest only (`gpunit/spec.py:13`, `:103-104`; `gpunit/serve/table.py:90`).
3. **F3, the weights (HF → pod, B5; `serve` only).** `vllm serve <repo> --revision <40-hex>` (`serve/launch.py:19-35`; `gpunit/serve/table.py:111-112`), into `HF_HOME` on the window volume when one is mounted (`serve/launch.py:14-16`). Telemetry is off (`serve/Dockerfile:8`); request logging is off (`gpunit/serve/models.toml:9`, `:20`).
4. **F4, the container log (pod → RunPod → laptop, B1).** Boot's lines: the ceiling, steps, the `gpunit host key <nonce>: SHA256:…` line, the exit code (`boot/boot.py:63-66`, `:260`, `:269`, `:243`). The command's and vLLM's stdout and stderr go there too. The laptop reads it over TLS (`gpunit/runpod.py:182-210`). `serve` copies it to `pod.log`, mode 0600, as read (`gpunit/serve/session.py:182-205`), and prints its lines with control characters removed (`gpunit/log.py:54-62`). RunPod's retention of a pod's container log is **undocumented**; Serverless logs are kept 90 days ([serverless logs](https://docs.runpod.io/serverless/development/logs#missing-logs)).
5. **F5, the host key and SSH (laptop → pod sshd, B2).** `ssh-keyscan` of the public host:port, compared with the fingerprint read in F4, then `ssh -F none -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes` with a per-session key (`gpunit/lifecycle.py:402-443`, `:125-143`). Nothing connects before the two agree.
6. **F6, the tunnel (laptop loopback ↔ pod loopback, B2 + B3).** `ssh -N -L<local>:localhost:<remote>`, `ExitOnForwardFailure`, `BatchMode` (`gpunit/library.py:284-287`); reopened with backoff when it dies and its local port is free, refused and torn down when another process holds the port (`gpunit/library.py:219-239`). It carries A7 (isekai's photographs, chat prompts) and A6 as a Bearer header. The SSH channel encrypts it; the local end is open to every local uid (T9, T37).
7. **F7, the pod's stop (pod → API, B1).** `POST /v2/pods/{id}/action {"action":"stop"}` with A2 in a header, through an opener that follows no redirect (`boot/boot.py:85-106`, `:69-82`), retried until a 200 (`boot/boot.py:109-126`). A stop clears the container disk ([stop a pod](https://docs.runpod.io/pods/manage-pods#stop-a-pod)).
8. **F8, teardown, volumes and billing (laptop → API, B1).** Delete and sweep by name and image (`gpunit/lifecycle.py:189-230`; `gpunit/runpod.py:340-353`), volume create and delete (`gpunit/runpod.py:313-338`), billing reads (`gpunit/runpod.py:212-233`).
9. **F9, the window volume (pod ↔ RunPod storage, B6).** Mounted at `/runpod-volume` (`gpunit/runpod.py:139-144`). It lives until `volume down` or the first gpunit command past its end (`gpunit/lifecycle.py:233-252`). It cannot be encrypted, and S3 keys reach it without a pod ([storage types](https://docs.runpod.io/pods/storage/types#encrypted-volumes), [S3 API](https://docs.runpod.io/storage/s3-api)).
10. **F10, local state (B3).** `.gpunit/`: dir set to 0700 on every write, keys 0600 (`gpunit/state.py:113-152`). The ledger: dir 0700, file 0600 (`gpunit/ledger.py:67-75`). `serve`'s home: dir 0700 (`gpunit/serve/session.py:73`).
11. **F11, `serve --api` (laptop stdout → agent).** `OPENAI_BASE_URL` and `OPENAI_API_KEY` printed to stdout (`gpunit/serve/session.py:245-246`). Requests go to 127.0.0.1 through the tunnel with no proxy (`gpunit/serve/session.py:63`).
12. **F12, the laptop command's env (`gpunit run`).** `os.environ` without `RUNPOD_API_KEY`, plus `GPUNIT_HOST`, `GPUNIT_SSH` and `GPUNIT_PORT_*` (`gpunit/run.py:52-59`).

## 4. Threats

Status: `mitigated` holds today · `partly` holds with a residual · `gap` does not hold · `accepted` settled as a residual. Evidence is a spec scenario key, a doc, or a converge finding (`.minions/findings/<change>_security.md`, gitignored).

| id | threat | actor | asset | mitigation in force | status | evidence |
|---|---|---|---|---|---|---|
| **Spoofing** | | | | | | |
| T1 | A MITM or DNS hijack stands in for the RunPod API | network | A1, A12 | hard-coded `https://api.runpod.io/v2` (`gpunit/runpod.py:30`, `boot/boot.py:28`); stdlib HTTPS verifies certificates by default (PEP 476) | mitigated | no test pins the TLS verification (not verified by the gate) |
| T2 | An API redirect carries the account key to another host | network, API path | A1 | `_NoRedirect` opener (`gpunit/runpod.py:56-69`, `:84`) | mitigated | `spec:secrets:redirect-not-followed` |
| T3 | A redirect on the pod's stop carries the pod key elsewhere | network, API path | A2 | boot's `_NoRedirect` opener follows no redirect (`boot/boot.py:69-82`, `:98`) | mitigated | 0012 security S3, verified |
| T4 | A redirected stop is read as success: urllib follows a 30x, the target's 200 ends the retries, and the pod bills with no ceiling left | network, API path | A12 | `_NoRedirect` opener in `boot.py` (`boot/boot.py:69-82`, `:98`; `fa98cdf`, 0012's converge) | mitigated | 0012 security S5, closed by `fa98cdf` |
| T5 | MITM on the first SSH contact to the pod | network | A3, A7 | the fingerprint is read over the authenticated API log, compared with a keyscan, and pinned in `known_hosts` with `StrictHostKeyChecking=yes` (`gpunit/lifecycle.py:402-443`, `:125-143`) | mitigated | `session:hostkey:match-recorded`, `session:hostkey:mismatch-tears-down` |
| T6 | A command's output forges the host-key line | the command's output | A4 | a per-pod nonce in the key line, a whole-line match, the line accepted only before `step: the command` (`gpunit/provider.py:11`, `:32-45`); the command gets no nonce (`boot/boot.py:40`, `:232`) | mitigated | `session:hostkey:echoed-line-is-ignored`, `session:hostkey:other-nonce-ignored`, `boot:child:no-nonce` |
| T7 | A root command reads the nonce from boot's `/proc` and forges the line | the command | A4 | none; such a command already holds root and A2 | accepted | 0009 design D3; README step 3 |
| T8 | sshd serves a host key or an authorized key baked into the image | B5 image | A4, pod | a fresh host key in a new temp dir and boot's own `sshd_config` with one `HostKey` and `AllowUsers root` (`boot/boot.py:43-56`, `:174-207`); `authorized_keys` overwritten (`:182-188`); the serve image deletes host keys (`serve/Dockerfile:6-7`) | mitigated | `boot:sshd:root-only`, `boot:sshd:authorized-key` |
| T9 | A local user squats the tunnel's local port and receives the command's or chat's traffic and the vLLM Bearer key | other local users | A6, A7 | `_taken` probes `127.0.0.1` and `::1` (`gpunit/library.py:306-318`) before `up` (`:299-303`), again before the tunnel opens (`:113-118`), and when the tunnel exits or a reopen is due (`:219-239`); a taken port refuses through `_Signals.refuse` (`:184-188`) and the session tears down; `serve` picks a free port first (`gpunit/serve/session.py:137-141`). Residual: a squatter that binds in the seconds between `ssh`'s start and its bind; `serve`'s first poll (`gpunit/serve/session.py:272-281`) may reach it then | partly | `run:ports:busy-on-v6-refuses`, `run:tunnel:taken-port-refuses`, `library:tunnel:taken-port-refuses`, `library:tunnel:taken-before-open-refuses` |
| T10 | The sweep deletes a look-alike pod that is not gpunit's | other account users | A12 | name plus image repository match, look-alikes ignored (`gpunit/runpod.py:340-353`, `:382-384`) | mitigated | `session:one:look-alike-image-ignored` |
| **Tampering** | | | | | | |
| T11 | The consumer's image is swapped under a tag | B5 | A13, A7 | only `@sha256:<64 hex>` is accepted (`gpunit/spec.py:13`, `:103-104`) | mitigated | `spec:image:tag-refused` |
| T12 | The serve image or its build is swapped | B5 | A13, A6, A7 | the digest pinned in `gpunit/serve/models.toml:2`; the base by digest (`serve/Dockerfile:3`); CI on manual dispatch, actions pinned by SHA, `persist-credentials: false` (`.github/workflows/build-serve-image.yml:5-51`) | mitigated | `serve:image:pinned-inputs`, `serve:image:only-a-request-builds` |
| T13 | Model weights are swapped on Hugging Face | B5 | A13 | the revision must be a 40-hex commit (`gpunit/serve/table.py:16`, `:111-112`); no `--trust-remote-code` (`serve/launch.py:19-35`) | mitigated | `serve:table:revision-pinned` |
| T14 | `boot.py` is tampered with in a consumer image | B5 GitHub tag | A2, A4, A12 | `ADD --checksum=sha256:` (README step 2), but the checksum is taken from the tag at build time (README step 2), trust on first use | partly | README only; no published checksum |
| T15 | The gpunit package is installed from a moved git tag | B5 | A1, A13 | no runtime dependency (`pyproject.toml:8`); install from `@v0.8.0`, a mutable tag (README step 3); a consumer's lock pinning the commit is not verified | partly | `pyproject.toml:8` |
| T16 | The serve image's `openssh-server` ages into a pre-auth CVE on the public port 22 | B5, network | pod root | the image digest freezes the packages; apt is not pinned at build (`serve/Dockerfile:6`); no rebuild cadence | partly | none |
| T17 | A local user plants or alters `.gpunit/pod`, `known_hosts` or `key` | other local users | A3, A4 | every write sets `.gpunit/` to 0700, a found directory too (`gpunit/state.py:143-146`) | mitigated | `session:key:dir-private` |
| **Repudiation** | | | | | | |
| T18 | Spend or a pod cannot be attributed, or the local ledger is edited | operator, local | A11, A12 | an append-only JSONL, 0600 (`gpunit/ledger.py:67-75`); amounts always from RunPod billing (`gpunit/spend.py:67-72`); RunPod keeps an account audit log ([audit logs](https://docs.runpod.io/accounts-billing/manage-accounts#monitor-account-activity)) | accepted | `spend:report:total-is-the-providers`, `spend:ledger:holds-nothing-else` |
| **Information disclosure** | | | | | | |
| T19 | The account key shows in argv or a process list | other local users | A1 | header only; no subprocess carries it (`gpunit/runpod.py:355-365`); CLAUDE.md invariant *the key never on argv* | mitigated | `spec:secrets:no-key-refused`; `test_gpu_reads_the_memory_and_the_secure_price` |
| T20 | The account key is read from a `.env` or committed | operator error | A1 | read from the environment only (`gpunit/runpod.py:80-83`); README suggests `export RUNPOD_API_KEY=...`, which can land in shell history (README step 3) | mitigated | `spec:secrets:dotenv-ignored` |
| T21 | `gpunit run` hands the account key to the consumer's laptop command | the consumer's command | A1 | `_command` drops `RUNPOD_API_KEY` from the command's env (`gpunit/run.py:52`) | mitigated | `run:handover:no-account-key` |
| T22 | The account key carries more power than gpunit needs (an **All** key) | a leaked A1 | A1, A12, every pod and volume | README *The account key* names gpunit's calls, and a restricted key covers them (G6, [§7](#7-the-probe)). The docs list per-API levels (None, Restricted per Serverless endpoint, Read/Write, Read Only), not REST-v2 scopes, so the key still reaches every pod and volume of the account ([credentials](https://docs.runpod.io/get-started/credentials#create-an-api-key)) | partly | G6 measured, 2026-10-18 |
| T23 | The command reads the pod key from boot's `/proc` | the command | A2 | kept out of the child's env (`boot/boot.py:40`, `:232`); the residual is documented (README step 3) | accepted | `boot:child:no-key` |
| T24 | The pod-scoped key can do more than stop its own pod: list or create pods, read other pods' env and logs, delete volumes, register SSH keys | the command, a tampered image | A2, A6, A8, A9, A10, A12 | RunPod scopes it: it lists no pods or volumes and reads no other pod (G5, [§7](#7-the-probe)). It reads its own pod, env included, and the account's pod and volume billing; writes to other pods were not tried. RunPod calls it a "Pod-scoped API key" without defining its scope ([env vars](https://docs.runpod.io/pods/templates/environment-variables#runpod-provided-variables)); the billing read is documented (README *Accepted risks*) | partly | G5 measured, 2026-10-18 |
| T25 | Secrets put in `[env]` sit in plain pod env, readable through the API and console, and kept on a stopped pod until `down` | API and console readers (B6) | A8 | `GPUNIT_*` and `RUNPOD_*` names refused (`gpunit/spec.py:198-206`); a `{{ RUNPOD_SECRET_<name> }}` value passes as written, and README *Secrets* points to it ([secrets](https://docs.runpod.io/pods/templates/secrets#direct-reference-method)) | partly | `spec:file:env-gpunit-refused`, `spec:file:env-secret-reference-kept`; whether the placeholder resolves through v2 `create` is not verified |
| T26 | A consumer puts its account key in `[env]` as `RUNPOD_API_KEY`, so the pod holds A1 | operator error | A1 | `RUNPOD_*` names are refused in `[env]` (`gpunit/spec.py:202-203`) | mitigated | `spec:file:env-runpod-refused` |
| T27 | The vLLM key in pod env is readable through the API and console | B6 | A6 | it lives one session (`gpunit/serve/session.py:57`); documented (README *Serve a model*) | accepted | `serve:api:key-required` |
| T28 | The vLLM key on `--api` stdout reaches agent logs or scrollback | Hermes' host | A6 | by design: the hand-off to the agent; one session; never on argv (`serve/launch.py:17-18`) | accepted | `serve:api:prints-the-endpoint` |
| T29 | The consumer's data lands in the container log, readable by account keys while the pod exists, retention undocumented | B6, RunPod | A7, A9 | boot's own lines hold nothing of the consumer's (`boot/boot.py:63-66`, `:260`, `:269`); the local copy is 0600 (`gpunit/serve/session.py:196`); README *Where your data lands* tells the consumer to keep data off stdout | partly | `serve:wait:log-kept`; RunPod pod-log retention undocumented |
| T30 | vLLM logs prompts (Hermes', the chat's) into the container log | vLLM default | A7, A9 | each row passes `--no-enable-log-requests` (`gpunit/serve/models.toml:9`, `:20`); vLLM `v0.31.0` defaults request logging off (`enable_log_requests: bool = False` in `vllm/engine/arg_utils.py` at the tag) | mitigated | `serve:table:request-logging-off`; the flag not yet run on a pod |
| T31 | The window volume keeps data past the session: unencrypted, reachable by S3 keys, deleted only by the next gpunit command past its end | B6, time | A10, A7 | a volume ceiling, a sweep on every verb (`gpunit/lifecycle.py:233-252`), the overdue volume named by `spend` (`gpunit/spend.py:82-88`), the residual documented (README *Working window*, *Where your data lands*); network volumes cannot be encrypted ([storage types](https://docs.runpod.io/pods/storage/types#encrypted-volumes)) | partly | `volume:ceiling:overdue-deleted`, `spend:report:overdue-volume-named` |
| T32 | The container disk outlives the session | RunPod | A7 | container disk only, no volume disk (`gpunit/runpod.py:150`); RunPod clears the container disk on stop ([stop a pod](https://docs.runpod.io/pods/manage-pods#stop-a-pod)) | mitigated | RunPod doc; the wipe of a deleted pod's disk is undocumented |
| T33 | A host operator reads pod memory or disk (isekai's photographs) | RunPod host | A7 | Secure Cloud only (`gpunit/runpod.py:151`); the ToS forbids inspection; Secure Cloud partners hold SOC 2, ISO 27001, PCI DSS ([security](https://docs.runpod.io/references/security-and-compliance)); documented (README *Accepted risks*) | accepted | `session:create:secure-and-22` |
| T34 | A pod lands in a jurisdiction the data must not reach (GDPR) | placement | A7 | `datacenters`, an allow-list (`gpunit/spec.py:33`, `:107-110`): the create names it (`gpunit/runpod.py:131-132`); a mounted volume outside it refuses (`gpunit/lifecycle.py:92-101`); the wait reads the pod's `dataCenterId` (`gpunit/runpod.py:177`) and tears down a pod outside it (`gpunit/lifecycle.py:376-387`); `volume up`'s stock choice stays within it (`gpunit/volume.py:200-216`). No `compliance` or country key (Q7) | mitigated | `session:datacenters:create-names-them`, `session:datacenters:volume-outside-refuses`, `session:datacenters:pod-outside-tears-down`, `volume:up:datacenter-within-allow-list` |
| T35 | A local user reads the session key, `pod.log` or the ledger | other local users | A3, A9, A11 | key 0600 (`gpunit/state.py:134-135`), dir 0700 (`:144-146`), `pod.log` 0600 (`gpunit/serve/session.py:196`), ledger 0600 in a 0700 dir (`gpunit/ledger.py:70-71`) | mitigated | `session:key:fresh-per-session`, `session:key:dir-private` |
| T36 | A leaked laptop key (backup, sync folder, commit) gives root on the live pod | key holder | A3, A7 | per-session (`gpunit/state.py:113-136`), deleted at teardown (`:138-141`), a warning when `.gpunit/` is not gitignored (`gpunit/lifecycle.py:289-303`); the key is unencrypted (`-N ""`) and lives in the project dir, documented (README *Accepted risks*, G16) | accepted | `session:key:deleted-at-teardown` |
| T37 | Another local user connects to a `run` or library forwarded port and uses the pod's app (isekai's renderer) | other local users | A7 | loopback-only bind (default `GatewayPorts`, `-F none`; `gpunit/library.py:284-287`); no auth for `run` ports, documented (README *Accepted risks*, G4); `serve` is guarded by the vLLM key | accepted | `serve:api:key-required` (serve only) |
| T38 | The laptop's process list shows the pod's host, port and key path | other local users | A3 (path only) | argv holds no secret (`gpunit/lifecycle.py:125-143`); the key file is 0600 | mitigated | `session:ssh:own-config-only` |
| T39 | Untrusted log lines carry terminal escape sequences into the operator's terminal | the command's output | operator terminal | `log.clean` removes C0, DEL and C1 (`gpunit/log.py:54-62`) from each printed line (`gpunit/serve/session.py:229`, `:267`); `pod.log` keeps the line as read | mitigated | `serve:wait:log-lines-cleaned` |
| T40 | The chat transcript persists on disk | local | A7 | kept in memory only (`gpunit/serve/chat.py:28`, `:37`) | mitigated | `serve:chat:streams` |
| T41 | A proxy env var routes the loopback request, with its Bearer key, to a proxy | the local env | A6 | `ProxyHandler({})` for the endpoint (`gpunit/serve/session.py:63`); API calls honour `HTTPS_PROXY` through a CONNECT tunnel, so TLS holds (`gpunit/runpod.py:84`) | mitigated | 0005 design (no proxy) |
| T42 | The serve image phones home (HF and vLLM usage stats) | B5 | A7 metadata | `DO_NOT_TRACK`, `HF_HUB_DISABLE_TELEMETRY`, `VLLM_NO_USAGE_STATS` (`serve/Dockerfile:8`) | mitigated | none |
| **Denial and spend** | | | | | | |
| T43 | The laptop dies, or gpunit is SIGKILLed, and the pod runs on | operator, crash | A12 | the ceiling is required (`gpunit/spec.py:25`, `:105`); a forked watchdog (`boot/boot.py:155-171`); a stop on any end (`:277-278`); RunPod's default $80/h account spend limit ([spend limits](https://docs.runpod.io/accounts-billing/manage-accounts#account-spend-limits)) | mitigated | `spec:ceiling:required`, `boot:stop:ceiling`, `boot:stop:command-end` |
| T44 | The pod's stop never succeeds (no CA store, 401/403, outage) | env, RunPod | A12 | an image with no CA store is refused before the arm (`boot/boot.py:129-134`, `:141-145`); retries with backoff, the cause named (`boot/boot.py:104-126`); a stopped pod still bills storage until `down` (README *The spend rules*) | partly | `boot:refuse:no-ca-store`, `boot:stop:retries`, `boot:stop:refused-key-named`; 0012 S4 |
| T45 | The root command kills the watchdog or boot | the command | A12 | none on the pod; the laptop's `down` still deletes | accepted | — |
| T46 | A lost create leaves a pod nobody records | network | A12 | a `pending` mark, exit 3, sweep by name and image (`gpunit/lifecycle.py:109-116`, `:339-358`) | mitigated | `session:lost:5xx-exits-3`, `session:lost:transport-exits-3` |
| T47 | A failed teardown strands a pod | RunPod, network | A12 | `TeardownFailed`, the record kept, a 404 never read as gone (`gpunit/library.py:96-104`, `:134-138`; `gpunit/lifecycle.py:197-203`, `:481-486`); the ceiling as backstop | partly | `session:down:404-keeps-record`, `run:teardown:failure-is-1` |
| T48 | A forgotten window volume bills, and keeps data, past its end | operator | A10, A12 | deleted by the next gpunit command; named by `spend`; the residual documented (README *Working window*) | accepted | `spend:report:overdue-volume-named` |
| T49 | A sweep deletes another checkout's or teammate's volume | other account users | A10 | the recorded volume only; a sweep by name only after a lost create, ledger-known volumes skipped, a terminal `y` required (`gpunit/volume.py:73-151`) | mitigated | `volume:down:sweep-needs-a-terminal` |
| T50 | A long ceiling, and no price gate on `run` and `up` | operator | A12 | `serve` and `volume up` ask the price (`gpunit/serve/session.py:144-179`, `gpunit/volume.py:219-235`); `run` and `up` filter on optional `max_hourly` only (`gpunit/lifecycle.py:318-336`); no upper bound on the ceiling (`gpunit/spec.py:75-83`) | accepted | `serve:price:no-by-default` |
| **Elevation** | | | | | | |
| T51 | The command runs as root in the pod, beside boot | the command | A2, A5 | none; documented (README step 3) | accepted | `boot:child:code` |
| T52 | sshd config weaknesses: passwords, other users | network | pod root | `PermitRootLogin prohibit-password`, `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `AllowUsers root`, one `HostKey` (`boot/boot.py:47-56`); forwarding stays on, since the tunnel needs it | mitigated | `boot:sshd:pam-on`, `boot:sshd:root-only` |
| T53 | The user's ssh_config or agent leaks to the pod (agent forwarding, other identities) | the pod | the operator's other keys | `-F none -o IdentitiesOnly=yes -i <session key>` (`gpunit/lifecycle.py:127-143`) | mitigated | `session:ssh:own-config-only` |
| T54 | The account's registered SSH keys reach the pod, through injection into `authorized_keys` or RunPod's SSH proxy | holders of account SSH keys | pod root, A7 | gpunit sets `PUBLIC_KEY` itself (`gpunit/runpod.py:126`) and does not send `startSsh`, which injects account keys "unless the request already sets one" ([create a pod](https://docs.runpod.io/api-reference-v2/pods/create-a-pod)); boot overwrites `authorized_keys` (`boot/boot.py:182-188`). But the credentials page says account keys are "injected into all your Pods… dynamically" ([credentials](https://docs.runpod.io/get-started/credentials#ssh-public-keys)), and `ssh.proxy` reaches a pod without a port ([get a pod](https://docs.runpod.io/api-reference-v2/pods/get-a-pod)). Measured: `authorized_keys` holds the session key alone, but an account key opens a root shell through `ssh.proxy` (G12, [§7](#7-the-probe)); gpunit cannot close the proxy, so README *Accepted risks* names it | accepted | G12 measured, 2026-10-18 |

Counts: 54 threats. **mitigated 30 · partly 11 · gap 0 · accepted 13.**

STRIDE by flow, as an index for completeness (— means no threat found on that flow):

| flow | S | T | R | I | D | E |
|---|---|---|---|---|---|---|
| F1 create | T1, T2 | T11 | T18 | T19, T20, T22, T25, T26, T34 | T46, T50 | — |
| F2 image pull | — | T11, T12, T14 | — | T42 | — | T8 |
| F3 weights | — | T13 | — | T42 | — | — |
| F4 container log | T6, T7 | — | — | T29, T30, T39 | — | — |
| F5 host key, SSH | T5, T8 | T16, T17 | — | T38 | — | T52, T53, T54 |
| F6 tunnel | T9 | — | — | T37, T41 | — | — |
| F7 pod's stop | T3, T4 | — | — | T23, T24 | T43, T44, T45 | T51 |
| F8 teardown, volumes, billing | T2, T10 | — | T18 | T22 | T47, T48, T49 | — |
| F9 window volume | — | — | — | T31 | T48 | — |
| F10 local state | — | T17 | T18 | T35, T36, T40 | — | — |
| F11 `serve --api` | T9 | — | — | T27, T28, T41 | — | — |
| F12 laptop command env | — | — | — | T21 | — | — |
| pod at rest (memory, disk) | — | — | — | T32, T33 | — | T51 |
| install (gpunit on the laptop) | — | T15 | — | — | — | — |

## 5. Gaps

Each gap the model found, and what became of it at `v0.9`. Sizes: line · small · design change.

| id | what | size | closes | outcome |
|---|---|---|---|---|
| G1 | Open the stop through a no-redirect opener (as `gpunit/runpod.py:56-69`), so a 30x is retried | line | T4 | **closed in v0.8** by `fa98cdf`, 0012's converge (`boot/boot.py:69-82`) |
| G2 | Drop `RUNPOD_API_KEY` from the laptop command's env in `run._command` | line | T21 | **closed in v0.9** (`gpunit/run.py:52`); the CHANGELOG names the break |
| G3 | Treat a taken port at the tunnel's exit as a refusal, not a reopen; probe `::1` too; keep the Bearer key off a port the tunnel never held | small | T9 | **closed in v0.9**, but for the seconds between `ssh`'s start and its bind: T9 stays `partly` |
| G4 | Document that every local uid can reach `GPUNIT_PORT_*`; a multi-user laptop needs app auth. Unix-socket forwards are a design change | small (doc) | T37 | **accepted and documented** (README *Accepted risks*); a card for unix sockets, trigger: a consumer on a shared machine |
| G5 | A metered live probe of the pod-scoped key: list pods, read another pod, list volumes, read billing. Record what it can do | small (live) | T24 | **measured in v0.9** ([§7](#7-the-probe)): the key is scoped to its own pod but reads the account's billing; T23's acceptance stands, T24 is `partly` |
| G6 | Name the minimum account key: probe a Restricted key against gpunit's calls (catalogue, pods CRUD + logs, network volumes CRUD, billing read). Document it, or say "All" is required | small (live + doc) | T22 | **measured in v0.9** ([§7](#7-the-probe)): a restricted key covers every call; README *The account key* names the calls and the minimum |
| G7 | Refuse `RUNPOD_*` names in `[env]` (except a `{{ RUNPOD_SECRET_… }}` value); document secrets for tokens. Prove the placeholder resolves through v2 `create` | small | T25, T26 | **closed in v0.9** for the refusal and the docs (`gpunit/spec.py:202-203`, README *Secrets*); the placeholder's substitution is unproven, trigger: a consumer that puts a token in a secret |
| G8 | Pod placement: a `gpunit.toml` key for data centres, sent as `dataCenterIds`. A window volume's data centre checked against it | design change | T34 | **closed in v0.9** by `datacenters`; no `compliance` or country key (Q7) |
| G9 | Verify vLLM v0.31's request-logging default; pin the quiet flag in each row's `args` | line | T30 | **closed in v0.9:** off by default at `v0.31.0`, and `--no-enable-log-requests` in each row (`gpunit/serve/models.toml:9`, `:20`) |
| G10 | A README "where your data lands" section: pod env, the container log, the window volume, `pod.log` and the ledger on the laptop. The consumer keeps data off stdout and the volume | small (doc) | T25, T29, T31, T33 | **closed in v0.9** (README *Where your data lands*) |
| G11 | Strip control characters from pod-log lines before they reach stderr | line | T39 | **closed in v0.9** (`gpunit/log.py:54-62`) |
| G12 | A live probe: do account SSH keys reach a gpunit pod (`authorized_keys` after boot, `ssh.proxy`)? If yes, document "register no account SSH keys", or check `authorized_keys` from the laptop | small (live) | T54 | **measured in v0.9** ([§7](#7-the-probe)): account keys reach the pod through `ssh.proxy`, not `authorized_keys`; documented (README *Accepted risks*), since no gpunit code can close the proxy |
| G13 | `chmod 0700` on `.gpunit/` at every `_mkdir`, not only on creation | line | T17 | **closed in v0.9** (`gpunit/state.py:146`) |
| G14 | Publish `boot.py`'s sha256 and the commit for each tag in the release notes; README installs gpunit by commit | small (doc) | T14, T15 | **a card**, trigger: the next release |
| G15 | A rebuild cadence for the serve image (openssh, vLLM) | small | T16 | **a card**, trigger: an OpenSSH CVE or a vLLM bump |
| G16 | The session key is unencrypted in the project dir, which may be synced or backed up | design change (move it to the state dir) | T36 | **accepted and documented** (README *Accepted risks*): the key is per-session and dies with the pod; trigger: a consumer whose project folder is synced |

## 6. Sources

**RunPod docs**
- [Runpod-provided environment variables](https://docs.runpod.io/pods/templates/environment-variables#runpod-provided-variables): `RUNPOD_API_KEY` is "Pod-scoped API key"; `PUBLIC_KEY`
- [Connect to Runpod](https://docs.runpod.io/get-started/connect-to-runpod) and [runpodctl overview](https://docs.runpod.io/runpodctl/overview): "a Pod-scoped API key"; its scope is not defined
- [Manage credentials](https://docs.runpod.io/get-started/credentials): API key permissions (All, Restricted, Read Only; per-API None, Restricted, Read/Write, Read Only); S3 keys; account SSH keys "injected into all your Pods"
- [Manage secrets](https://docs.runpod.io/pods/templates/secrets): `{{ RUNPOD_SECRET_name }}`; values never shown after creation; [create a secret (v2)](https://docs.runpod.io/api-reference-v2/account/create-a-secret)
- [Create a pod (v2)](https://docs.runpod.io/api-reference-v2/pods/create-a-pod): `env`, `cloud` (SECURE = Runpod-owned datacenter hardware), `dataCenterIds` ("Preferred data centers for placement"), `startSsh` and `PUBLIC_KEY`
- [Get a pod (v2)](https://docs.runpod.io/api-reference-v2/pods/get-a-pod) and [list pods (v2)](https://docs.runpod.io/api-reference-v2/pods/list-pods): `env` returned; `dataCenterId`; `ssh.proxy`, `ssh.direct`
- [Stream pod logs (v2)](https://docs.runpod.io/api-reference-v2/pods/stream-pod-logs): container and system logs, tail at most 5000; retention not stated
- [Serverless logs](https://docs.runpod.io/serverless/development/logs#missing-logs): 90-day retention, Serverless only
- [Manage pods: stop](https://docs.runpod.io/pods/manage-pods#stop-a-pod): container disk cleared on stop
- [Storage types: encrypted volumes](https://docs.runpod.io/pods/storage/types#encrypted-volumes): container disk and network volumes cannot be encrypted
- [S3-compatible API](https://docs.runpod.io/storage/s3-api): volume access without a pod; no bucket encryption
- [Security and compliance](https://docs.runpod.io/references/security-and-compliance): container isolation, host access policy, GDPR for EU regions, Secure Cloud SOC 2, ISO 27001, PCI DSS
- [Choose a pod: Secure vs Community](https://docs.runpod.io/pods/choose-a-pod#secure-cloud-vs-community-cloud)
- [List data centers (v2)](https://docs.runpod.io/api-reference-v2/catalog/list-data-centers) and [get a GPU type (v2)](https://docs.runpod.io/api-reference-v2/catalog/get-a-gpu-type): `compliance` filter (GDPR, ISO_IEC_27001, SOC_2_TYPE_2, HIPAA, …), `countryCodes`
- [Manage accounts](https://docs.runpod.io/accounts-billing/manage-accounts): team roles, the $80/h default spend limit, audit logs
- [Use SSH](https://docs.runpod.io/pods/configuration/use-ssh): proxied SSH; account keys injected
- Undocumented: what the pod-scoped key may call; the restricted-key scopes for REST v2 pods, network volumes and billing; pod container-log retention; disk sanitisation on delete; confidential computing

**vLLM `v0.31.0`**, the serve image's base (`serve/Dockerfile:3`)
- `vllm/engine/arg_utils.py`: `enable_log_requests: bool = False`, a `BooleanOptionalAction`, so `--no-enable-log-requests` is the explicit off
- `vllm/entrypoints/launchers/cli_args.py`: `enable_log_outputs: bool = False`, which requires `--enable-log-requests`

**gpunit at `v0.9`**
- `boot/boot.py`, `serve/Dockerfile`, `serve/launch.py`, `.github/workflows/build-serve-image.yml`, `pyproject.toml`
- `gpunit/{cli,spec,state,provider,runpod,lifecycle,library,run,log,ledger,spend,volume}.py`, `gpunit/serve/{session,table,chat}.py`, `gpunit/serve/models.toml`
- `README.md` (step 2, step 3, *Serve a model*, *Working window*, *Security and privacy*, *The spend rules*), `CLAUDE.md` (invariants)
- `openspec/specs/{boot,library,run,serve,session,spec,spend,volume}/spec.md` (scenario keys above)
- `openspec/changes/archive/0001-core/design.md` D3, D8; `0002-paydown/design.md` D1, D4, D9; `0005-serve/design.md` D6; `0009-paydown/design.md` D3; `0012-boot-in-python/design.md` D4; `0013-secure-and-private/design.md`
- `.minions/findings/0012-boot-in-python_security.md` (S3, S4 verified; S5 closed by `fa98cdf`)

## 7. The probe

What RunPod leaves undocumented, measured once by hand and metered (0013 design D15): G6 with a restricted key through `make live`, `make live-volume` and `gpunit spend`; G5 and G12 from a `live` pod's shell, beside a second pod. Each result is a line below, and T22, T24 and T54 take their status from it.

- **G6 measured:** on 2026-10-18 a restricted key, made in the console at its narrowest settings, ran `make live`, `make live-volume` and `gpunit spend --days 1` with no 401 or 403 (`live/last_run.txt`). So a restricted key covers every call gpunit makes; RunPod offers no REST v2 scope finer than the account's pods, volumes and billing.
- **G5 measured:** the pod-scoped key, read from a `live` pod's `/proc`, on 2026-10-18: `GET pods` 403; `GET pods/<own>` 200, its env included (`GPUNIT_CEILING`, `GPUNIT_NONCE`, `PUBLIC_KEY`); `GET pods/<other>` 404, for a live pod of the same account; `GET network-volumes` 403; `GET billing/pods` 200, the account's records for every pod; `GET billing/networkvolumes` 200. No write was tried.
- **G12 measured:** with an SSH key registered in the account, on 2026-10-18: the pod's `/root/.ssh/authorized_keys` held the session key alone, equal to the laptop's `.gpunit/key.pub`, at once and five minutes after `up`. The account key opened a root shell on the same pod through its `ssh.proxy`, `<pod id>-<n>@ssh.runpod.io`, which wants a terminal: RunPod's proxy authenticates the account key itself, beside the pod's sshd.
