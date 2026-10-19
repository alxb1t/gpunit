# Proofs

The live proofs rent real pods and volumes, by hand, never in CI; each prints the price and the most it can cost
first (decision D6). The gate, `make gate`, fakes every provider answer. Each run is kept, dated and named by its
change, in a tail: `live/last_run.txt`, `live/serve_last_run.txt` and `live/spend_last_run.txt`.

## The latest runs

Each quote is a line its tail holds, word for word.

- **Placed, host key verified, torn down:** [`live/last_run.txt`](../live/last_run.txt), `make live`, 2026-10-19,
  `0015-architecture-and-docs`.

  ```
  2026-10-19T11:23:06Z host key verified: SHA256:IYHJbbQ7n3hLVHufmDykmbQs63v1B5hwfgS71yJPP/Q
  2026-10-19T11:23:09Z pod jwfe3sbrm03w99 deleted
  no session is recorded
  ```

- **A dead container ended by the dead-pod rule:** [`live/last_run.txt`](../live/last_run.txt), `make live-dead`,
  2026-10-17, `0012-boot-in-python`.

  ```
  2026-10-17T15:47:39Z refused: pod sfv6ql737yuakr got no host and port 22 within 120s
  up exited 1 after 126s
  no session is recorded
  ```

- **A tool call on the `qwen3.8-27b` row:** [`live/serve_last_run.txt`](../live/serve_last_run.txt),
  `make live-serve MODEL=qwen3.8-27b`, 2026-10-13, `0008-a-30b-class-row`.

  ```
  2026-10-13T11:41:56Z qwen3.8-27b answers on http://127.0.0.1:52269/v1
  tool call: get_weather {"city": "Paris"}
  ```

- **A user file's row served:** [`live/serve_last_run.txt`](../live/serve_last_run.txt),
  `make live-serve granite-4.0-micro`, 2026-10-18, `0014-your-own-rows`.

  ```
  2026-10-18T15:36:13Z granite-4.0-micro answers on http://127.0.0.1:52857/v1
  tool call: get_weather {"city": "Paris"}
  2026-10-18T15:45:37Z volume t7332e85q8 deleted
  ```

- **Spend matched the console to the cent:** [`live/spend_last_run.txt`](../live/spend_last_run.txt),
  `gpunit spend --days 7`, 2026-10-12, `0007-spend`.

  ```
  totals equal to the cent: gpunit $1.80, console $1.796
  ```

## `make live`

`make live` rents one real pod for at most ten minutes plus its 420s wait for SSH: it prints the card's price and the
maximum first, then runs `nvidia-smi` through `gpunit run`.

Latest run: 2026-10-19, `0015-architecture-and-docs`, in [`live/last_run.txt`](../live/last_run.txt).

## `make live-volume`

`make live-volume` opens a [working window](usage.md#working-window) of 10 GB for at most 30 minutes: one pod writes
the UTC time to the volume, a new pod reads it back, and the target fails unless the lines are equal. Each pod runs
for at most ten minutes plus its 420s wait for SSH.

Latest run: 2026-10-18, `0013-secure-and-private`, in [`live/last_run.txt`](../live/last_run.txt).

## `make live-serve`

`make live-serve MODEL=<row>` proves the serve image and a row on one of its cards, for at most 30 minutes plus the
1200s wait for SSH a session, inside the row's working window: `gpunit serve <row> --api` downloads the weights into
the volume for one chat request and one tool call through [live/tool_call.py](../live/tool_call.py), then a chat of
one prompt loads them from it. `MODEL` defaults to `qwen3-4b`. The volume bills for at most an hour.
A user file's row: `GPUNIT_MODELS=live/models.toml make live-serve MODEL=granite-4.0-micro`.

Latest run: 2026-10-18, `0014-your-own-rows`, in [`live/serve_last_run.txt`](../live/serve_last_run.txt).

## `make live-dead`

`make live-dead` boots an image whose container exits at once, for at most its 120s wait, and passes when `up` exits
`1` and prints its refusal as `reason: <line>`, then deletes what `up` left; a failed `gpunit down` fails it.
In a checkout that records a pod it exits `1` and rents nothing. RunPod may restart such a container, so the reason
can be the 120s wait's end.

Latest run: 2026-10-17, `0012-boot-in-python`, in [`live/last_run.txt`](../live/last_run.txt).

## `make live-serve-dead`

`make live-serve-dead` serves `qwen3-4b` with an argument vLLM refuses, inside its working window, through
[live/serve_dead.py](../live/serve_dead.py): it passes when the dead-pod refusal, the crash's lines from `pod.log` and
the delete within 15s all show. It is the dead-pod rule's live proof. Its pod runs for at most 600s plus the 1200s
wait for SSH, and the volume for at most an hour.

Latest run: 2026-10-16, `0010-on-demand-volumes`, in [`live/serve_last_run.txt`](../live/serve_last_run.txt).
