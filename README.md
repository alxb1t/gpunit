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

The design: [openspec/changes/0001-core/design.md](openspec/changes/0001-core/design.md), archived under
`openspec/changes/archive/` once released.

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
   volume = "<network volume id>"              # pins the data centre, mounted at /runpod-volume
   ports = [8188, { remote = 8080, local = 18080 }]
   ram_gb = 32
   cuda = "12.8"
   max_hourly = 0.80
   timeout = 420                               # seconds to wait for SSH
   [env]
   MODE = "render"
   ```

2. **Make `boot.sh` the image's entrypoint.** It needs `openssh-server` in the image, and BuildKit for
   the checksum; on an older Docker, copy the file in.

   ```dockerfile
   ADD --checksum=sha256:<digest> https://raw.githubusercontent.com/alxb1t/gpunit/v0.1.0/boot/boot.sh /opt/gpunit/boot.sh
   RUN chmod +x /opt/gpunit/boot.sh
   ENTRYPOINT ["/opt/gpunit/boot.sh", "--"]
   CMD ["python3", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
   ```

   `<digest>` is the file's sha256 at the tag: `curl -sL <the URL above> | shasum -a 256`.

3. **Install and run.** The key comes from the environment alone; gpunit reads no `.env`.

   ```sh
   uv add --dev git+https://github.com/alxb1t/gpunit@v0.1.0
   echo .gpunit/ >> .gitignore
   export RUNPOD_API_KEY=...
   uv run gpunit run -- python3 render.py
   ```

   The command sees `GPUNIT_HOST`, `GPUNIT_PORT_<remote>=<local>` for each port, and `GPUNIT_SSH`, a command
   line that opens a shell on the pod. gpunit does not wait for the app: the command polls its own port.

## The verbs

Each verb reads `gpunit.toml` from the working directory, or the file `--spec <path>` names.

| verb | does |
|---|---|
| `gpunit up` | places a pod, waits for SSH, verifies its host key, records it in `.gpunit/` |
| `gpunit status [--json]` | prints the recorded session to stdout |
| `gpunit ssh` | opens a shell on the recorded pod |
| `gpunit down` | deletes the recorded pod, then every other live pod of the project |
| `gpunit run -- <cmd>` | `up`, the tunnel, `<cmd>`, then `down`, however `<cmd>` ends |

| exit | means |
|---|---|
| `0` | done; for `run`, the command's own code passes through |
| `1` | refused or failed; the teardown failed |
| `2` | usage: an unknown verb, a missing command, an unreadable spec path |
| `3` | a create's answer was lost; a pod may exist and bill — run `gpunit down` |
| `128+n` | `run` was stopped by signal `n` and tore down |

gpunit's own lines go to stderr, each opening with the UTC time; stdout belongs to the command.

## The spend rules

- **The ceiling is required.** `boot.sh` stops the pod at it, whatever happens to the laptop.
- **The pod stops; `down` deletes.** A stopped pod bills storage, not GPU, until the next `gpunit down`.
- **A 404 is not "gone".** A wrong key gets a 404 too; `down` keeps the record and exits `1`.
- **A lost create exits `3`.** `.gpunit/pending` stays, and `down` sweeps every live `gpunit-<project>` pod.
- **One session per project.** `up` refuses on a record, a pending create, or a listed pod.
- **Secure cloud, port 22 only.** Other ports reach the laptop over the SSH tunnel, never a public proxy.
- **A fresh keypair per session**, in `.gpunit/`, deleted with the pod.

## The proof — `make live`

`make live` rents one real pod for at most ten minutes, run by hand: it prints the card's price and the
maximum first, then runs `nvidia-smi` through `gpunit run`. The gate, `make gate`, fakes every provider answer.
