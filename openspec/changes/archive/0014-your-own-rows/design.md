# Design — 0014 your own rows

How `serve` finds the **user file**, merges its rows with the bundled ones, checks them, and keeps logging off for
every row; then the docs, the `0013` cards, the image and the proof. **Verdict: feasible** — every caller already
reads one function of `gpunit/serve/table.py`, and `serve/launch.py` is the one place every row passes through.

## Context

See [proposal](proposal.md) — *Why*. Terms used throughout:

- **bundled table** — `gpunit/serve/models.toml`, in the package: the image's digest and gpunit's rows.
- **user file** — the operator's own `models.toml`, outside every repo; it holds rows alone.
- **user row** — a row of the user file. **bundled row** — a row of the bundled table.

What holds at the cut, `main` at `76f87fd` (`v0.9.0`):

- **The table:** `TABLE = Path(__file__).with_name("models.toml")` (`gpunit/serve/table.py:12`); `load(path)` checks
  the image digest, each field's type, the revision as 40 hex and no space inside an argument (`:83-130`); `Row`
  (`:30-72`) and `Table` (`:75-80`) are frozen dataclasses.
- **The callers:** `cli._known` (`gpunit/cli.py:214-217`, called at `:135`); `session.serve` (`gpunit/serve/session.py:56`),
  `down` (`:101`) and `_window_spec` (`:121`), which `volume_up` and `volume_down` call (`:109`, `:117`).
  `live/serve_dead.py:66-75` replaces `table.load` on the module.
- **The rows' flag:** `"--no-enable-log-requests"` ends each bundled row's `args` (`gpunit/serve/models.toml:9`,
  `:20`); `tests/test_serve_table.py:54-60` asserts it, and `:115-122` asserts `qwen3-4b`'s `SERVE_ARGS` with it.
- **The image's quiet:** `ENV DO_NOT_TRACK=1 HF_HUB_DISABLE_TELEMETRY=1 VLLM_NO_USAGE_STATS=1`
  (`serve/Dockerfile:8`); `serve/launch.py:12-35` sets `HF_HOME` and `exec`s `vllm serve` with `SERVE_ARGS` last;
  `tests/test_serve_image.py:133-136` asserts that argv word for word.
- **The usage error:** `no model {model!r} in the table; it holds {', '.join(models)}` (`gpunit/cli.py:217`);
  `tests/test_cli.py:124-139` asserts `it holds qwen3-4b, qwen3.8-27b`.
- **The tests' home:** `tests/conftest.py:53-58` points `HOME` at a temp directory; nothing clears
  `GPUNIT_MODELS` or `XDG_CONFIG_HOME`, so a developer's own file would reach the tests.
- **The brief's premises:** each holds at `76f87fd` but one: `load` ends at `:130`, not `:136`. The brief read
  `f3262de` and the `v0.9` branch.
- **The cards:** each card's *Still true?* holds at `76f87fd`, read against the archived paths ([D9](#d9),
  [D10](#d10)). `0013·R5`'s passing console settings are recorded nowhere in the repo: `live/last_run.txt:470` says
  only "a console-made restricted key".

## Goals / Non-Goals

**Goals:** a person serves their own model without editing gpunit; no row can turn request logging or telemetry on;
the user path proven on a real pod with a model of another family.

**Non-Goals:** a per-row image; gated models; a verb to list rows; several user files; checking a user row's other
vLLM arguments.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | one user file: `--models`, else `GPUNIT_MODELS`, else the XDG default; a named file must read, an absent default is no rows | a file outside every repo needs no gitignore (Q1) | merging every file found |
| [D2](#d2) | `table.rows` returns the bundled rows and the user rows; a same name replaces; the CLI prints one line | the live runs keep their rows (Q2) | refusing a same name |
| [D3](#d3) | a user row passes `_row`'s checks on the bundled image; the user file holds `models` alone | one rule for every row (Q3, Q9) | an `image` key per file |
| [D4](#d4) | `--enable-log-requests` in any row's `args` is refused | no row can turn logging on (Q4) | stripping it silently |
| [D5](#d5) | the usage error names each row with its source | no new verb (Q6) | a `gpunit models` verb |
| [D6](#d6) | `serve/launch.py` sets the telemetry variables and passes `--no-enable-log-requests` last; the bundled rows lose the flag | only gpunit's launcher sees every row (Q4) | the flag kept per row |
| [D7](#d7) | `--models <path>` on `serve`, `down`, `volume up` and `volume down`, refused without a model | each verb on a row must find it (Q1) | an environment variable alone |
| [D8](#d8) | README's *Your own rows*, `CLAUDE.md`'s layout, the threat model's F13 and T55 | the user file is a new input; the trust-boundary rule | — |
| [D9](#d9) | `0013·R1`, `R2`, `R3`, `R5`, `S4`, `S5` fixed in live text and code | the cards' fixes | — |
| [D10](#d10) | `0013·R6` and `R7` close won't-fix | they name the archived `0013` change or the released `[0.9.0]` entry | editing released text |
| [D11](#d11) | the serve image rebuilt as `v0.10-rc1` and re-pinned | `serve/launch.py` changed | — |
| [D12](#d12) | `make live-serve` on `live/models.toml`'s `granite-4.0-micro`, through `GPUNIT_MODELS` | the user path end to end, on another family (Q7) | a Qwen row |

### D1

`table.user_file(given: Path | None) -> Path | None`, in `gpunit/serve/table.py`:

```
given (--models)            set ─▶ given
GPUNIT_MODELS, non-empty    set ─▶ Path(GPUNIT_MODELS)
XDG_CONFIG_HOME, absolute   set ─▶ $XDG_CONFIG_HOME/gpunit/models.toml ┐ a file ─▶ it
otherwise                       ─▶ ~/.config/gpunit/models.toml        ┘ none   ─▶ None
```

- **A named file is read, or refused:** `load`'s `OSError` refusal already names the path, e.g.
  `rows.toml: [Errno 2] No such file or directory: 'rows.toml'`; the CLI exits `1`.
- **A relative `XDG_CONFIG_HOME` is ignored,** as the XDG base directory spec says.
- **The tests:** `tests/conftest.py`'s `isolated_home` gains `monkeypatch.delenv("GPUNIT_MODELS", raising=False)` and
  `monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)`.

### D2

`table.rows(given: Path | None = None) -> Table`:

```
bundled = load()                        # the module's `load`, so live/serve_dead.py's patch still applies
path = user_file(given); None ─▶ bundled
own = the user file's rows, on bundled.image          (D3)
Table(image, models={**bundled.models, **own}, user=path, replaced=sorted(own ∩ bundled))
```

- **`Table`** gains `user: Path | None = None` and `replaced: tuple[str, ...] = ()`; **`Row`** gains
  `source: str = "bundled"`, the user file's path for a user row.
- **The callers:** `cli._known`, `session.serve`, `session.down` and `session._window_spec` read `table.rows(...)`
  in place of `table.load()`. `load` stays the one-file reader.
- **The replace line:** `cli._known` prints it, once per command, when `replaced` is not empty:
  `log.say(f"{found.user} replaces the bundled {', '.join(found.replaced)}")`, e.g.
  `2026-10-18T10:00:00Z /home/ada/.config/gpunit/models.toml replaces the bundled qwen3-4b`.

### D3

- **The shape:** the user file is TOML holding `[models.<name>]` tables alone. A top-level key other than `models`
  refuses `{path}: unknown key {key!r}; a user file holds [models.<name>] rows alone, served on the bundled image`.
  An absent or empty `models` refuses as the bundled table does: `{path}: 'models' must hold at least one row`.
- **Each row** goes through `_row(path, name, bundled.image, raw)`: the same fields, types, 40-hex revision and
  no-space check, its refusal naming `{path}: models.{name}`.
- **An example user file** (README's, and `live/models.toml`'s row, [D12](#d12)):

```
# ~/.config/gpunit/models.toml — rows alone; every row runs the bundled gpunit-vllm image
[models."granite-4.0-micro"]
repo = "ibm-granite/granite-4.0-micro"
revision = "56111ae135df9c53a78c99028e7bc24035a9e979"
served = "granite-4.0-micro"
args = ["--max-model-len", "16384", "--enable-auto-tool-choice", "--tool-call-parser", "hermes"]
vram_gb = 24
gpus = ["NVIDIA RTX A5000", "NVIDIA GeForce RTX 4090", "NVIDIA L4"]
disk_gb = 40
```

### D4

`_args` (`gpunit/serve/table.py:126-130`) refuses `--enable-log-requests` after the space check:
`{where}: 'args' holds --enable-log-requests; request logging stays off`. It covers bundled and user rows alike.
[D6](#d6)'s last-place flag is the enforcement; this refusal tells the operator at once.

### D5

`cli._known(model: str, models: Path | None)`:

```
no model 'x' in the table; it holds granite-4.0-micro (/home/ada/.config/gpunit/models.toml), qwen3-4b (bundled), qwen3.8-27b (bundled)
```

Sorted by name. A replaced row names the user file. A bad user file refuses before the name is looked up, and
`_run`'s `except log.Refusal` (`gpunit/cli.py:140-141`) exits `1`.

### D6

`serve/launch.py`, before the `exec`:

```
os.environ.update(DO_NOT_TRACK="1", HF_HUB_DISABLE_TELEMETRY="1", VLLM_NO_USAGE_STATS="1")
argv: … --port 8000 <SERVE_ARGS split> --no-enable-log-requests
```

- **Last:** vLLM's `--enable-log-requests` is a `BooleanOptionalAction`, and argparse keeps the last occurrence, so a
  row cannot outvote it.
- **The Dockerfile's `ENV` stays:** a shell opened with `gpunit ssh` keeps the same quiet.
- **The bundled rows** drop `"--no-enable-log-requests"` (`gpunit/serve/models.toml:9`, `:20`).
- **The tests:** `tests/test_serve_image.py`'s `ARGS` gains ` --no-enable-log-requests`; a new test binds
  `serve:image:launcher-forces-quiet` with a vLLM stub that prints `DO_NOT_TRACK`, `HF_HUB_DISABLE_TELEMETRY` and
  `VLLM_NO_USAGE_STATS`.
  `tests/test_serve_table.py`'s `SERVE_ARGS` string drops the flag, and `test_no_row_logs_requests` asserts no row
  holds `--enable-log-requests` or `--enable-log-outputs`.

### D7

`gpunit/cli.py`:

- **`_parser`:** `add_argument("--models", type=Path)` on `serve`, on `down`, and on `volume up` and `volume down`.
- **`parse`:** after `args.model` is set, `--models` with no model raises `Usage("--models goes with --serve")`.
- **`_run` and `_serve`:** `_known(args.model, args.models)`; each session call gets `models=args.models`.
- **`USAGE`:** `gpunit serve <model> --ceiling 2h [--api] [--models PATH] | gpunit down --serve <model> [--models PATH]`,
  and `[--models PATH]` after `--serve <model>` in the `volume up` and `volume down` forms.

`gpunit/serve/session.py`: `serve`, `down`, `volume_up`, `volume_down` and `_window_spec` take
`models: Path | None = None` and read `table.rows(models)`.

### D8

- **README:**
  - *Serve a model*'s intro: "The models it knows are rows of gpunit/serve/models.toml" gains "and of
    [your own file](#your-own-rows)".
  - A new `### Your own rows`, before `### From a container`: the lookup diagram from [D1](#d1), the example file from
    [D3](#d3), and these commands:

```
mkdir -p ~/.config/gpunit && $EDITOR ~/.config/gpunit/models.toml
uv run gpunit serve granite-4.0-micro --ceiling 1h
uv run gpunit serve granite-4.0-micro --ceiling 1h --models ./models.toml
GPUNIT_MODELS=~/agents/box/models.toml uv run gpunit serve granite-4.0-micro --ceiling 1h --api
uv run gpunit down --serve granite-4.0-micro --models ./models.toml
```

  - Its bullets: one file is read, never merged; a same name replaces the bundled row, said in one line; a user row
    passes the bundled checks; no `image` key; request logging and telemetry are off whatever a row says, and
    `--enable-log-requests` is refused; `down --serve` and `volume … --serve` need the same file as `serve`.
  - *The verbs*: "`serve` and each `--serve` read the bundled model table instead" → "`serve` and each `--serve`
    read the bundled model table and [your own rows](#your-own-rows) instead"; `[--models PATH]` in the `serve`,
    `down --serve` and `volume … --serve` rows.
  - *The proof*'s `make live-serve` paragraph: after "`MODEL` defaults to `qwen3-4b`." add "A user file's row:
    `GPUNIT_MODELS=live/models.toml make live-serve MODEL=granite-4.0-micro`."
- **`CLAUDE.md`'s layout:** `table.py` (a row's `Spec`) → `table.py` (a row's `Spec`; the user file's lookup and
  merge); **`serve/launch.py`** — its command: `HF_HOME` on a volume, then vLLM → `HF_HOME` on a volume, logging and
  telemetry off, then vLLM; `live/`'s line gains `live/models.toml`, the user file `make live-serve` proves.
- **`docs/threat-model.md`:**
  - **F13**, a new item after F12, and **T55**, a new Tampering row after T17, each one line, word for word below;
    `(cite)` is `table.py`'s lines as the build wrote them.
  - **T13**'s mitigation: "no `--trust-remote-code` (`serve/launch.py:19-35`)" → "no bundled row passes
    `--trust-remote-code`; a user row may (T55)".
  - **The quiet moves to the launcher:** F3's "Telemetry is off (`serve/Dockerfile:8`); request logging is off
    (`gpunit/serve/models.toml:9`, `:20`)" → "Telemetry and request logging are off for every row, set by
    `serve/launch.py` (cite its lines), telemetry in the image too (`serve/Dockerfile:8`)". T30 and T42 cite
    `serve/launch.py`, and gain `serve:image:launcher-forces-quiet` as evidence. G9's outcome, "and `--no-enable-log-requests`
    in each row (`gpunit/serve/models.toml:9`, `:20`)" → "and `--no-enable-log-requests` in each row; since v0.10
    `serve/launch.py` passes it for every row".
  - **The counts:** `Counts: 54 threats. **mitigated 29 · partly 12 · gap 0 · accepted 13.**` →
    `Counts: 55 threats. **mitigated 28 · partly 14 · gap 0 · accepted 13.**`; the STRIDE index gains the row
    `| F13 user file | — | T55 | — | — | — | — |`. Line 3's and *Sources*' `v0.9` → `v0.10`.

```
13. **F13, the user file (operator → gpunit, B3).** Read from `--models`, `GPUNIT_MODELS` or `$XDG_CONFIG_HOME/gpunit/models.toml` (`gpunit/serve/table.py:(cite)`). Its rows choose the repository, the revision and vLLM's arguments run on the pod, on the bundled image.

| T55 | A user row turns request logging on, runs an unpinned model, or runs the repository's own code | the operator, or a tool running as them | A7, A9, A13 | the bundled rows' checks: a 40-hex revision, no space in an argument (`gpunit/serve/table.py:(cite)`); `--enable-log-requests` refused; `serve/launch.py` turns logging and telemetry off last; no `image` key. Other vLLM arguments pass as written, `--trust-remote-code` among them, its code pinned by the revision | partly | `serve:rows:checked-as-bundled`, `serve:rows:logging-on-refused`, `serve:rows:image-refused`, `serve:image:launcher-forces-quiet` |
```

### D9

- **`0013·R1`** — `docs/threat-model.md`'s `gpunit/spec.py` and `gpunit/volume.py` citations, re-read at `76f87fd`.
  The threat model's line numbers move with [D8](#d8), so each is named by its row:

| row | before | after |
|---|---|---|
| F2, T11 | `gpunit/spec.py:13`, `:103-104` | `gpunit/spec.py:13`, `:107-108` |
| T25 | `gpunit/spec.py:198-206` | `gpunit/spec.py:199-207` |
| T26, G7 | `gpunit/spec.py:202-203` | `gpunit/spec.py:203-204` |
| T34 | `gpunit/spec.py:33`, `:107-110`; `gpunit/volume.py:200-216` | `gpunit/spec.py:33`, `:111-116`; `gpunit/volume.py:194` |
| T43 | `gpunit/spec.py:25`, `:105` | `gpunit/spec.py:25`, `:101-103` |
| T50 | `gpunit/volume.py:219-235`; `gpunit/spec.py:75-83` | `gpunit/volume.py:216-232`; `gpunit/spec.py:79-87` |

  T49's `gpunit/volume.py:73-151` still holds. No task of this change edits `gpunit/spec.py` or `gpunit/volume.py`.
- **`0013·R2`** — README *Where your data lands*, the laptop bullet: "the ledger, ids and times alone, is at `0600`" →
  "the ledger, pod and volume ids, project, card, image and times, is at `0600`" (`gpunit/ledger.py:52-54`).
- **`0013·R3`** — `gpunit/serve/session.py:138`: `# Picked before the price, so a busy local port is never refused
  after a yes.` → `# Picked before the price, so a port busy on 127.0.0.1 is never refused after a yes.`
- **`0013·R5`** — README's `- **Measured minimum:**` and the threat model's `- **G6 measured:**` say "at its narrowest
  settings". The settings are recorded nowhere, so the **HUMAN** names them at [D12](#d12)'s run, on the key it uses.
- **`0013·S4`** — `log.clean(text: str, keep: str = "") -> str` deletes each control character not in `keep`;
  `chat._stream` (`gpunit/serve/chat.py:101-102`) writes `log.clean(part, keep="\n\t")` and keeps `part` as streamed
  in `parts`. T39's mitigation names the chat (`gpunit/serve/chat.py`), and its evidence gains
  `serve:chat:streamed-text-cleaned`.
- **`0013·S5`** — T34's mitigation and README *Placement* gain: "`serve` takes no `datacenters` yet: a served model's
  pod and its window volume go wherever RunPod places them." T34 moves to `partly` in phase 5, with the counts: `serve` pods ignore `datacenters` (settled at the cut).

### D10

- **`0013·R6`:** design D14 and task 6.2 of `openspec/changes/archive/0013-secure-and-private/` (`design.md:275`)
  record what held then (`0008·R5`, `0012` D11).
- **`0013·R7`:** `CHANGELOG.md:36`, in the released `[0.9.0]`.
- **They close won't-fix**, listed in the proposal's `backlog:`. No task edits them.

### D11

`serve/launch.py` is baked into the image, so the pinned `gpunit-vllm` runs `v0.9`'s launcher until a rebuild. The
**HUMAN** pushes the branch, runs `.github/workflows/build-serve-image.yml` with the tag `v0.10-rc1`, and writes the
new digest into `gpunit/serve/models.toml:2`, replacing
`1a83cf6c73421810210eabb14772c892bbf3086359486c1676da02725dd8ee8b`.

### D12

**`live/models.toml`** is a user file, tracked as the proof's input, holding [D3](#d3)'s `granite-4.0-micro` row.

| measure | value | command |
|---|---|---|
| `ibm-granite/granite-4.0-micro` at the cut | `sha` `56111ae135df9c53a78c99028e7bc24035a9e979`, `gated` false | `curl -s https://huggingface.co/api/models/ibm-granite/granite-4.0-micro` |
| its weights | 6805711176 bytes, in 2 safetensors files | `curl -s https://huggingface.co/api/models/ibm-granite/granite-4.0-micro/tree/56111ae135df9c53a78c99028e7bc24035a9e979` |
| its tool tokens | `<tool_call>`, `</tool_call>` in `tokenizer_config.json` | the same revision's `tokenizer_config.json` |

- **Why this model:** IBM's Granite, not Qwen; Apache 2.0 and ungated; 3B, so a 24 GB card holds it with room; it
  writes tool calls as `<tool_call>{…}</tool_call>`, the format vLLM's `hermes` parser reads, so
  `live/tool_call.py` can pass.
- **The run:** `GPUNIT_MODELS=live/models.toml make live-serve MODEL=granite-4.0-micro`. `live/serve.py` runs
  `gpunit serve`, `volume up --serve` and `volume down --serve` as children, which inherit `GPUNIT_MODELS`; no live
  script changes.
- **The restricted key** names `0013·R5`'s settings: made in the RunPod console, each per-API setting noted, as
  narrow as the console allows; a 401 or 403 widens one setting and the run goes again. `uv run gpunit spend --days 1`
  on it covers the billing read `make live-serve` does not.
- **The tail** goes to `live/serve_last_run.txt` under `<date> — make live-serve granite-4.0-micro, 0014-your-own-rows`.

## Dependencies

None.

## Risks / Trade-offs

- **The bundled rows lose their flag before the image is rebuilt** → between phase 3 and [D11](#d11), the pinned
  image's launcher passes no flag; vLLM `v0.31.0` logs no request by default, and no metered run happens before the
  re-pin.
- **A user row can pass `--trust-remote-code`** → the repository's code runs on the pod, pinned by the revision; T55
  names it, `partly`.
- **`down --serve` without the file `serve` used** cannot find a user row → the usage error names the rows it found;
  README says to pass the same file.
- **Granite's tool call through `hermes` is unproven here** → the metered run is the proof; a failed tool call is a
  halt, and its lines are kept.
- **The replace line is printed on every verb that names a replaced row** → one line per command, on stderr.

## Migration Plan

None for a consumer: with no user file, `serve` serves the bundled rows as before. Rollback is `v0.9.0`.

## Verdict

Feasible: a lookup and a merge in `gpunit/serve/table.py`, a flag through the CLI, the telemetry variables and the logging flag in
`serve/launch.py`. The image rebuild and one metered run are the only steps a person takes.
