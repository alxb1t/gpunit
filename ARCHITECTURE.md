# gpunit — architecture

How gpunit is built, why, and where to change it. For using gpunit, read [usage](docs/usage.md).

gpunit opens a RunPod GPU session from a laptop, runs work on it, and closes it, from the CLI or from Python. The
laptop half places a pod, proves its host key, tunnels its ports and tears it down; the pod half stops the pod at
its ceiling and whenever its command ends.

```
 laptop                                                    pod
 ──────                                                    ───
 cli ─┬─▶ run · serve ─▶ library ─▶ lifecycle ─▶ hostkey   boot/boot.py
      ├─▶ volume ─────────────────▶ lifecycle                ceiling watchdog, sshd,
      └─▶ spend                                              key line, the command, stop
                   library's tunnel: ssh -N -L ──────────▶ sshd :22
                                                           serve/launch.py ──▶ vLLM
 cli · library ─▶ providers.build ─▶ runpod, as the Provider
 lifecycle · volume · spend ─▶ Provider ◀─ runpod ─▶ RunPod REST v2 ◀── the container log
                               the seam              create · log · delete · billing
```

They meet at RunPod's API, which carries the create's env in and boot's lines out, and at the pod's sshd, which the
laptop reaches only after the key in the log matches the scan
([D22](docs/decisions.md#d22--the-host-key-is-proven-over-the-log)).

**The layers**, lowest last. A module imports its own layer and those below; each module's layer is in
[modules](docs/modules.md).

| layer | holds |
|---|---|
| interface | the verbs and their exit codes (`gpunit.cli`), and the public names (`gpunit`) |
| serve | a model's row, its price, the wait for the model, the chat or the `--api` hold |
| session | the session from Python and `run`: the `with` block, its signals, the tunnel, the teardown |
| lifecycle | `up`, `status`, `down` and `ssh`; the host key's proof; the window volume; `spend` |
| cloud | `providers.build`, which picks the provider, and `runpod`, the one `Provider` |
| model | the `Spec`, the `.gpunit/` files, the ledger, the boot contract and the `Provider` seam |
| foundation | gpunit's lines and its version |

## The map

| page | for |
|---|---|
| [usage](docs/usage.md) | how to use gpunit: from a project, from Python, and through `serve` |
| [proofs](docs/proofs.md) | the live proofs, what each proves, and their latest runs |
| [principles](docs/principles.md) | the words, and each rule with what holds it |
| [decisions](docs/decisions.md) | the decisions in force, each with why and what made it |
| [data-flow](docs/data-flow.md) | a session, the boot contract, the state files, `serve`, the window, `spend`, exit codes |
| [modules](docs/modules.md) | the layers, each module, where RunPod is built, the test seams |
| [extending](docs/extending.md) | a recipe for each kind of change, and the rules for a change |
| [pins](docs/pins.md) | each pin, where it is checked and how it moves |
| [threat-model](THREAT_MODEL.md) | what gpunit protects, from whom, and what holds |

## Where to start

| to | read |
|---|---|
| fix a bug in a session | [data-flow](docs/data-flow.md), then [modules](docs/modules.md) for the file |
| add a verb, a key or a row | [extending](docs/extending.md) |
| change what the pod runs | [extending](docs/extending.md#a-bootpy-change), then [pins](docs/pins.md) |
| change a secret, a file mode, a network call or a log line | [threat-model](THREAT_MODEL.md) first |
| learn why something is the way it is | [decisions](docs/decisions.md), then the archived change its *Made by* names |
| check what a rule rests on | [principles](docs/principles.md) |
