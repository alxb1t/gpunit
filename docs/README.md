# The guide to gpunit

How gpunit is built, why, and where to change it. For using gpunit, read the [project README](../README.md).

gpunit opens a RunPod GPU session from a laptop, runs work on it, and closes it, from the CLI or from Python. The
laptop half places a pod, proves its host key, tunnels its ports and tears it down; the pod half stops the pod at
its ceiling and whenever its command ends.

```
 laptop                                          pod
 ──────                                          ───
 cli ──▶ run · serve ──▶ library ──▶ lifecycle    boot/boot.py
              │             │          │   ▲        │  ceiling watchdog, sshd,
            volume       tunnel        │   │        │  key line, the command, stop
            spend        ssh -N -L ────┼───┼──────▶ sshd :22
                                       │   │
                                       ▼   │        serve/launch.py ──▶ vLLM
                          RunPod REST v2: create, log, delete
                                 ▲                         │
                                 └──── container log ◀─────┘
```

They meet at RunPod's API, which carries the create's env in and boot's lines out, and at the pod's sshd, which the
laptop reaches only after the key in the log matches the scan
([D22](decisions.md#d22--the-host-key-is-proven-over-the-log)).

**The layers**, lowest last: interface · serve · session · lifecycle · cloud · model · foundation. A module imports
its own layer and those below ([modules](modules.md)).

## The map

| page | for |
|---|---|
| [principles](principles.md) | the words, and each rule with what holds it |
| [decisions](decisions.md) | the decisions in force, each with why and what made it |
| [data-flow](data-flow.md) | a session, the boot contract, the state files, `serve`, the window, `spend`, exit codes |
| [modules](modules.md) | the layers, each module, where RunPod is built, the test seams |
| [extending](extending.md) | a recipe for each kind of change, and the rules for a change |
| [pins](pins.md) | each pin, where it is checked and how it moves |
| [threat-model](threat-model.md) | what gpunit protects, from whom, and what holds |

## Where to start

| to | read |
|---|---|
| fix a bug in a session | [data-flow](data-flow.md), then [modules](modules.md) for the file |
| add a verb, a key or a row | [extending](extending.md) |
| change what the pod runs | [extending](extending.md#a-bootpy-change), then [pins](pins.md) |
| change a secret, a file mode, a network call or a log line | [threat-model](threat-model.md) first |
| learn why something is the way it is | [decisions](decisions.md), then the archived change its *Made by* names |
| check what a rule rests on | [principles](principles.md) |
