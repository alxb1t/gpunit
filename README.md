# gpunit

**A RunPod GPU session any project can open, use and close.** One TOML file, one Dockerfile line, one command:
the pod is placed, its host key proven, the command run against it, and the pod torn down on every way out.

```
laptop                                           pod
gpunit run -- <cmd>                              boot.sh -- <cmd>
 ├─ up: place · wait · verify host key ────────▶  ceiling armed · sshd · fingerprint
 ├─ ssh -N -L <ports>  ◀─────────────────────────▶ sshd
 ├─ <cmd> with GPUNIT_HOST, GPUNIT_PORT_*, GPUNIT_SSH
 └─ down: delete · sweep                          stops itself at the ceiling
```

The design: [openspec/changes/archive/0001-core/design.md](openspec/changes/archive/0001-core/design.md).

## Use it from a project

1. **Write `gpunit.toml`** at the project root.

   ```toml
   project = "isekai"                          # the pod is named gpunit-isekai
   image = "ghcr.io/you/isekai@sha256:<64 hex>" # a digest, never a tag
   gpus = ["NVIDIA GeForce RTX 4090", "NVIDIA RTX A6000"]  # tried in order
   vram_gb = 24
   ceiling = "45m"                             # required: the pod stops itself after this
   disk_gb = 50
   # optional
   volume = "<network volume id>"              # pins the data centre; the pod sees GPUNIT_VOLUME_PATH
   ports = [8188, { remote = 8080, local = 18080 }]
   ram_gb = 32
   cuda = "12.8"
   max_hourly = 0.80
   timeout = 420                               # seconds to wait for SSH
   [env]
   MODE = "render"                             # GPUNIT_* names are gpunit's, and refused here
   ```

2. **Make `boot.sh` the image's entrypoint.** It needs `openssh-server`, `curl` and coreutils' `env` in the
   image, and BuildKit for the checksum; on an older Docker, copy the file in.

   ```dockerfile
   ADD --checksum=sha256:<digest> https://raw.githubusercontent.com/alxb1t/gpunit/v0.1.2/boot/boot.sh /opt/gpunit/boot.sh
   RUN chmod +x /opt/gpunit/boot.sh
   ENTRYPOINT ["/opt/gpunit/boot.sh", "--"]
   CMD ["python3", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
   ```

   `<digest>` is the file's sha256 at the tag: `curl -sL <the URL above> | shasum -a 256`.

3. **Install and run.** The key comes from the environment alone; gpunit reads no `.env`. The command's
   environment on the pod does not carry `RUNPOD_API_KEY`: boot keeps it to stop the pod. The command runs as
   root beside boot, though, so it can still read the key from boot's own environment in `/proc`; run nothing
   on the pod you would not trust with the key.

   ```sh
   uv add --dev git+https://github.com/alxb1t/gpunit@v0.1.2
   echo .gpunit/ >> .gitignore
   export RUNPOD_API_KEY=...
   uv run gpunit run -- python3 render.py
   ```

   The command sees `GPUNIT_HOST`, `GPUNIT_PORT_<remote>=<local>` for each port, and `GPUNIT_SSH`, a command
   line that opens a shell on the pod. gpunit does not wait for the app: the command polls its own port.

## Use it from Python

`gpunit.session()` is the session `gpunit run` opens, as a `with` block: the pod is torn down when the block
ends, however it ends.

```python
import subprocess

import gpunit

with gpunit.session("gpunit.toml", environ={"RUNPOD_API_KEY": key}, say=my_log) as s:
    url = f"http://127.0.0.1:{s.port(8188)}"
    subprocess.run([*s.ssh, "nvidia-smi"], check=True)
```

| attribute | is |
|---|---|
| `s.host` | the pod's public SSH host |
| `s.port(remote)` | the local port `remote` is forwarded to; `Refused` for a port not in `ports` |
| `s.ssh` | the `ssh` argv that opens a shell on the pod |
| `s.image` | the booted image |
| `s.pod_id` | the pod's id |

| raises | when | `gpunit run` exits |
|---|---|---|
| `gpunit.Refused` | it refused; nothing it rented is left | `1` |
| `gpunit.Lost` | a create's answer was lost; the sweep was attempted | `3` |
| `gpunit.TeardownFailed` | the teardown failed; `.gpunit/pod` is kept, so run `gpunit down`. Its `__cause__` is the exception that ended the block, if one did, or the `Refused` whose own teardown failed while the session opened | `1` |
| `gpunit.Interrupted` | `SIGINT`, `SIGTERM` or `SIGHUP` ended the block; a `KeyboardInterrupt` whose `.signal` names it | `128+n` |

- **The spec** is a path, or a `Spec` from `gpunit.load_spec`. `cwd` is where `.gpunit/` lives; it defaults to
  the working directory.
- **The key** is read from `environ` when given, else from the process's environment.
- **The lines** go to `say(line)` when given, else to stderr. The tunnel's thread calls `say` too, so it must be
  safe to call from another thread.
- **Signals:** while the block runs, `SIGINT`, `SIGTERM` and `SIGHUP` raise `Interrupted`; during the teardown
  they are ignored. Your own handlers are replaced for the block's life and set back when it closes.
- **The main thread:** open the session there; another thread gets `Refused`.
- **The tunnel** is reopened when it dies, as in `gpunit run`.

## The verbs

Each verb reads `gpunit.toml` from the working directory, or the file `--spec <path>` names.

| verb | does |
|---|---|
| `gpunit up` | places a pod, waits for SSH, verifies its host key, records it in `.gpunit/` |
| `gpunit status [--json]` | prints the recorded session to stdout |
| `gpunit ssh` | opens a shell on the recorded pod |
| `gpunit down` | deletes the recorded pod, then every other live pod of the project |
| `gpunit run -- <cmd>` | the Python session around `<cmd>`: `up`, the tunnel, `<cmd>`, then `down`, however `<cmd>` ends |

| exit | means |
|---|---|
| `0` | done; for `run`, the command's own code passes through |
| `1` | refused or failed; the teardown failed |
| `2` | usage: an unknown verb, a missing command, an unreadable spec path |
| `3` | a create's answer was lost; a pod may exist and bill — run `gpunit down` |
| `128+n` | signal `n` stopped `run` or killed its command, and the teardown succeeded; a failed teardown is still `1` |

gpunit's own lines go to stderr, each opening with the UTC time; stdout belongs to the command.

## The spend rules

- **The ceiling is required.** `boot.sh` stops the pod at it, whatever happens to the laptop.
- **The pod stops; `down` deletes.** A stopped pod bills storage, not GPU, until the next `gpunit down`.
- **A 404 is not "gone".** A wrong key gets a 404 too; `down` keeps the record and exits `1`.
- **A lost create exits `3`.** `.gpunit/pending` stays, and `down` sweeps every live `gpunit-<project>` pod.
- **One session per project.** `up` refuses on a record, a pending create, or a listed pod.
- **Secure cloud, port 22 only.** Other ports reach the laptop over the SSH tunnel, never a public proxy.
- **A fresh keypair per session**, in `.gpunit/`, deleted with the pod.
- **gpunit's ssh is its own.** No ssh_config is read, and only the session's key is offered; a user who wants
  their own config runs `ssh -i .gpunit/key` themselves.

## The proof — `make live`

`make live` rents one real pod for at most ten minutes, run by hand: it prints the card's price and the
maximum first, then runs `nvidia-smi` through `gpunit run`. The gate, `make gate`, fakes every provider answer.
