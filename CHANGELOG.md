# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

## [Unreleased]

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
