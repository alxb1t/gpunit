# A gone pod's record is cleared — tasks

The provider reads a pod and lists the account's, the rule clears a gone record, the word states it. Decisions are in [design](design.md).

## Progress

- [x] 1 — The provider reads one pod and lists the account's · moderate
- [x] 2 — The rule: `status` and `down` clear a gone record · hard
- [x] 3 — The word: D57, the guide, the threat model and the specs · moderate

## 1 — The provider reads one pod and lists the account's

- [x] 1.1 In `gpunit/provider.py`, add `pod(self, pod_id: str) -> PodInfo` to `Provider` after `get`, and `pod_ids(self) -> list[str]` after `volume_ids`, per [D1](design.md#d1) and [D2](design.md#d2). Docstrings follow `volume` and `volume_ids`: `pod` raises `Unknown` on a 404, else `Lost`; `pod_ids` raises `Lost`.
  Verify: `grep -n -E "def pod(_ids)?\(" gpunit/provider.py` prints a line for each.

- [x] 1.2 In `gpunit/runpod.py`, add `RunPod.pod` and `RunPod.pod_ids`. `pod` calls `GET /pods/<id>`, raises `Unknown(f"RunPod does not know pod {pod_id!r}")` on a 404, raises `Lost(_report(f"pod read of {pod_id!r}", answer))` on a body that does not parse, and builds its `PodInfo` by the code `get` builds it with, moved to one helper both call. `pod_ids` is `self._walk("/pods", "pods", "pod listing", lambda pod: str(pod["id"]))`. `get` still returns `None` on any failed read.
  Verify: `grep -n -E "def pod(_ids)?\(" gpunit/runpod.py` prints a line for each.

- [x] 1.3 In `tests/fakes.py`, give `FakeProvider` the keyword arguments `pods: Mapping[str, PodInfo | Exception] | None = None` and `account_pods: Sequence[str] | Exception = ()`, and the methods `pod` and `pod_ids` beside `volume` and `volume_ids`, each recording its call. `pod` answers the pod's script through `_raise_or`; an id not in `pods` raises `Lost("pod read")` ([D8](design.md#d8)). `pod_ids` answers `account_pods` through `_raise_or`.
  Verify: `grep -n -E "def pod(_ids)?\(" tests/fakes.py` prints a line for each.

- [x] 1.4 In `tests/test_runpod.py`, add `test_a_pod_read_answers_the_pod_unknown_or_lost`, parametrized as `test_an_unreadable_stock_is_unknown_or_lost` is, ids `200`, `404`, `500`: `200` with `fixture("pod_running.json")` gives `PodInfo("RUNNING", "203.0.113.7", 40022)`, `404` raises `Unknown`, `500` raises `Lost`. Mark it `session:down:gone-clears`. In `test_the_listing_names_the_projects_live_pods`, add a step: `pod_ids()` on a `page(...)` holding a `TERMINATED` pod and a pod of another name returns every id.
  Verify: `uv run pytest tests/test_runpod.py -q -k test_a_pod_read_answers_the_pod_unknown_or_lost` exits 0.

## 2 — The rule: `status` and `down` clear a gone record

- [x] 2.1 In `gpunit/lifecycle.py`, add `def pod_gone(provider: Provider, pod_id: str) -> bool` after `gone`, by the table in [D3](design.md#d3): `Unknown` from `provider.pod(pod_id)`, then `pod_id not in provider.pod_ids()`; a `Lost` from either returns `False`; a read that answers returns `False`. Docstring: `Return True when the pod's read answers 404 and the account's listing lacks it.` Comment the 404-and-wrong-key reason as `gone` does, citing decision D55; D57 lands in phase 3, and a comment citing a decision absent from `docs/decisions.md` fails the docs test.
  Verify: `grep -n "def pod_gone" gpunit/lifecycle.py` prints its line.

- [x] 2.2 In `lifecycle.status`, call `built().get(record.id)` as now; when it gave `None` and `pod_gone(built(), record.id)` holds, call `state.clear_session()`, `log.say(f"pod {record.id} is gone; its record is cleared")`, then print `"null" if as_json else "no session is recorded"` ([D4](design.md#d4)); else `_report` as now. A live pod makes no further call. The window line after it stays as it is.
  Verify: `grep -n "pod {record.id} is gone; its record is cleared" gpunit/lifecycle.py` prints a line.

- [x] 2.3 In `lifecycle._delete_pods`, add the branch of [D5](design.md#d5) between the `DELETED` branch and the `404` branch: `elif pod_gone(provider, record.id):` clears the session with `state.clear_session()` and says `f"pod {record.id} is gone; its record is cleared"`, and sets no `failed`. The 404 and other-code branches, their messages and the sweep stay as they are. `.gpunit/pending` and the ledger are untouched ([D6](design.md#d6)).
  Verify: `grep -n "elif pod_gone(provider, record.id):" gpunit/lifecycle.py` prints a line.

- [x] 2.4 In `tests/test_down.py`, parametrize `test_a_404_keeps_the_record` by ids `gone`, `listing-lost`, `still-listed`, each a `FakeProvider(deletes={"pod-1": 404}, pods={"pod-1": Unknown(...)}, account_pods=...)`. `gone`: `account_pods=[]` → exit `0`, `state.pod`, `state.known_hosts`, `state.key` and `state.key_pub` gone, stderr holds `pod pod-1 is gone; its record is cleared`, `ledger.deleted()` is empty. `listing-lost`: `account_pods=Lost("pod listing returned HTTP 403")` → exit `1`, record kept, stderr holds `the key may be wrong`. `still-listed`: `account_pods=["pod-1"]` → the same as `listing-lost`. Mark it with both `session:down:404-keeps-record` and `session:down:gone-clears`; keep its name, `docs/principles.md` cites it.
  Verify: `uv run pytest tests/test_down.py tests/test_library.py tests/test_run.py -q -k "test_a_404_keeps_the_record and gone"` exits 0.

- [x] 2.5 In `tests/test_status.py`, add `test_status_clears_a_gone_pod`, marked `cli:status:gone-clears` and `cli:status:listed-keeps-record`, ids `gone`, `still-listed`, `listing-lost`, `read-lost`, each with `gets=[None]` and a recorded `RECORD`. `gone` runs `["status", "--json"]` with `pods={"pod-1": Unknown(...)}` and `account_pods=[]`: stdout `null`, stderr holds the gone line, `State(cwd).read()` is `None`, exit `0`. `still-listed` and `listing-lost` keep the record and print `status=UNKNOWN`; `read-lost` has no `pods` script, so the read raises `Lost`, and keeps it too.
  Verify: `uv run pytest tests/test_down.py tests/test_status.py tests/test_runpod.py -q -k test_status_clears_a_gone_pod` exits 0.

## 3 — The word: D57, the guide, the threat model and the specs

- [x] 3.1 In `docs/decisions.md`, add D57 after D56, with the text in [D7](design.md#d7): title `A pod is gone when its read and the account's listing both lack it`, `Made by: 0021·D1`. **HALT CHECK**: `git grep -n "^### D5[67]" -- docs/decisions.md` prints only D56's heading before this task; if it prints D57 too, the id is taken and the plan is wrong.
  Verify: `git grep -n "^### D57 · A pod is gone" -- docs/decisions.md` prints its heading.

- [x] 3.2 In `docs/decisions.md`, retitle D23 `Teardown: the recorded pod and the project's pods are swept`, set its statement and Why to the text in [D7](design.md#d7), and end D55's last sentence with `A pod is gone by the same rule (decision D57).` in place of `A pod's `404` still keeps its record (decision D23).` Edit the D23 and D55 text where they stand.
  Verify: `git grep -n "^### D23 · Teardown: the recorded pod and the project's pods are swept" -- docs/decisions.md` prints its heading.

- [x] 3.3 Repoint D23's anchor to `d23--teardown-the-recorded-pod-and-the-projects-pods-are-swept` in `README.md`, `docs/principles.md` (each row citing it) and `docs/data-flow.md`, and state the new rule beside each link, linking D57's anchor `d57--a-pod-is-gone-when-its-read-and-the-accounts-listing-both-lack-it` where the line states the rule. In `docs/principles.md`, the row `A pod's 404 is never gone; …` becomes `A pod's 404 is gone only when the account's listing lacks it too, as a window volume's is`, from D57 and D55, held by the old tests plus `test_status_clears_a_gone_pod`.
  Verify: `git grep -n "d23--teardown-the-recorded-pod-and-the-projects-pods-are-swept" -- README.md docs/principles.md docs/data-flow.md` prints a line in each file.

- [x] 3.4 In `docs/principles.md`, in the row `Every input that shapes a pod is pinned`, replace the breach `—` with `breached: a draft model or LoRA another argument names is fetched unpinned (`gpunit/serve/table.py::_args`, T55)`, closing debt `0020·R7`. **HALT CHECK**: `git grep -n "def _args" -- gpunit/serve/table.py` prints a line.
  Verify: `grep -n "a draft model or LoRA another argument names is fetched unpinned" docs/principles.md` prints a line.

- [x] 3.5 In `docs/usage.md`, make the `status` row say it clears the record of a gone pod, and replace the bullet `A 404 is not "gone".` with the rule: a 404 clears a pod's record, in `status` and `down`, only when the account's listing lacks the pod too; a wrong key fails the listing and keeps it; a window volume follows the same rule (decisions D55, D57).
  Verify: `grep -n "D57" docs/usage.md` prints a line.

- [x] 3.6 In `docs/data-flow.md`, make the state line `pod: pending ──create answered──▶ pod ──down, 204──▶ (gone)` name the gone path as well (`status` and `down` clear a gone pod's record), and the `pod` bullet say `A 404 on delete keeps it unless the pod is gone`, linking D57's anchor.
  Verify: `grep -n "unless the pod is gone" docs/data-flow.md` prints a line.

- [x] 3.7 In `THREAT_MODEL.md`, edit T47: replace `a 404 never read as gone` with the rule, its controls `gpunit/lifecycle.py::pod_gone` and `gpunit/provider.py::Provider.pod_ids`, and the residual of [D6](design.md#d6): a key of another RunPod account reads a pod as gone, accepted because the person runs one account; a pod-scoped key fails the listing. Add `session:down:gone-clears` and `cli:status:gone-clears` to its evidence. Name the new line `pod <id> is gone; its record is cleared` in T47's controls: it holds a pod id gpunit already logs, no secret and no file.
  Verify: `grep -n "pod_gone" THREAT_MODEL.md` prints a line.
