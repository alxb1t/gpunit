# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

## [Unreleased]

## [0.1.2] - 2026-10-08

### Security

- `boot.sh` runs the command under `env -u RUNPOD_API_KEY`: the account-wide key stays boot's, for the stop,
  and is not in the command's environment. The command still runs as root beside boot, so it can read the key
  from boot's own environment in `/proc`; run no code on the pod you would not trust with the key. Boot refuses
  an image without coreutils' `env`.

### Fixed

- An interrupt before any create began tears nothing down: `run` no longer sweeps another working copy's pod
  of the same project, and says no create began. A record or pending marker left by an earlier `gpunit up`
  no longer counts as this run's create: an interrupt before `up` refuses deletes neither that session's pod
  nor any other listed one.
- A host-key line pushed out of the log's last 5000 lines is read again from the create's time, so a boot
  that logs heavily no longer tears a healthy pod down; `created` is stamped before the create.
- A stop answered `401` or `403` says the key cannot stop this pod and to delete it by hand, then retries,
  instead of an outage's message.
- README: the image needs coreutils' `env`, the command's environment on the pod does not carry
  `RUNPOD_API_KEY` (though a root command can still read it from boot's process), and the pins move to `v0.1.2`.
- `make live` passed on a rebuilt `live` image carrying this `boot.sh`: the host key verified, `nvidia-smi` ran
  over `GPUNIT_SSH`, and the pod was deleted; it is the first live run of `AllowUsers root`. The tail is in
  `live/last_run.txt`.

## [0.1.1] - 2026-10-08

### Security

- Every ssh line is gpunit's own: `-F none -o IdentitiesOnly=yes`, so a user's ssh_config cannot forward their
  agent, proxy or multiplex to the pod.
- The API client follows no redirect: a 3xx is read as a failed answer, so the key never reaches another host;
  the redirect test also shows an unguarded opener leaking the key.
- `boot.sh`'s sshd admits root alone (`AllowUsers root`), so a key the image baked in for another account, even a
  `!`-locked one, opens no login on the pod.

### Fixed

- `up` checks `ssh`, `ssh-keygen` and `ssh-keyscan` before any request, so a missing tool no longer leaks a pod;
  `gpunit ssh` without `ssh` refuses instead of a traceback.
- `gpunit.toml` refuses a port outside 1–65535 before anything is rented.
- A delete answering `200` is a success for `down` and the sweep, as it already was for `RunPod.delete`.
- The pod's log read ends once the stream is quiet for 3 s, not after a fixed 10 s; a stream that never goes
  quiet still ends at 10 s.
- `run` exits `128 + n` when signal `n` killed the command, as a shell does, not a negative code.
- A tunnel that keeps dying is reopened with backoff, 1 s doubling to 30 s, so it no longer floods stderr.
- `boot.sh` starts sshd with `UsePAM yes`, so a root whose password is locked with `!` still logs in by key.
- The curl refusal is its own test under `boot:refuse:no-curl`, apart from the sshd one.
- `session:ssh:no-ssh-refuses` is checked through the CLI too: `gpunit ssh` without `ssh` exits `1`.
- README: the design link points at the archive, the pins move to `v0.1.1`, a spend rule says gpunit's ssh is
  its own, and the `128+n` row covers a command killed by a signal.
- `make live` passed on a rebuilt `live` image carrying this `boot.sh` before `AllowUsers root`: the host key
  verified and `nvidia-smi` ran over `GPUNIT_SSH` under `-F none`, with sshd on `UsePAM yes`; the run's tail is in
  `live/last_run.txt`.

## [0.1.0] - 2026-10-07

### Added

- The `gpunit` package skeleton: the CLI parser with its usage exit `2`, `gpunit.toml` loaded strictly into
  a `Spec`, and the `.gpunit/` session files with a fresh keypair at `0600`.
- The gate grows to `uv sync`, ruff, ty and pytest before `openspec validate`, so the package is checked offline.
- The `Provider` seam and its RunPod implementation on `urllib`: the key only in a request header, a 400
  refused, a 5xx or a lost answer `Lost`, a listing that never reads a look-alike or a bare pod as ours.
- `gpunit up`, `status` and `down`: one create per card, a lost create exits `3` and is swept later, the wait
  and the host-key check tear down on failure, and `down` never reads a 404 as gone.
- `gpunit run -- <cmd>` and `gpunit ssh`: the session handed over in the environment, the tunnel reopened,
  teardown on exit and on every signal; a busy local port refuses before anything is rented.
- `boot/boot.sh`, the pod's half: the ceiling and an exit trap that stop the pod with backoff, sshd on a
  fresh host key, the fingerprint line, and the command as a child whose code is boot's.
- `README.md` and `CLAUDE.md` describe the package: a consumer's steps, the verbs and exit codes, the spend rules,
  the layout and the invariants.
- `make live`, the metered proof: a real pod placed, its host key verified and torn down, and a second pod
  stopped by its own ceiling; the run's tail is `live/last_run.txt`.

### Fixed

- RunPod requests send `User-Agent: gpunit/<version>`: RunPod's Cloudflare refused Python's default agent
  with a 403 (code 1010), which `make live` found.
- `gpunit run` exits `1` when a signal is followed by a failed teardown; it exited `128+n`, which reads as torn down.
- `boot.sh` makes a fresh host key in a new directory on every boot; it served any key the image baked in, as
  installing `openssh-server` on Debian or Ubuntu does.
- `boot.sh` refuses an image without `curl`; the ceiling's stop needs it, and without it retried forever.
- `boot.sh` starts sshd on a config of its own that names only the fresh host key; `-o HostKey` added it to
  the keys the image's `sshd_config` names, so an image naming its own `HostKey` lines served those too.
