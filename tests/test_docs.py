"""Hold the guide's citations, and the front page short: decision D50, decision D52."""

import ast
import functools
import re
import subprocess
from collections.abc import Collection
from pathlib import Path

import pytest

from tests.helpers import tree

ROOT = Path(__file__).resolve().parent.parent

# The roots scanned for citations: every tracked root but the specs and the archive.
SCANNED_DIRS = ("gpunit", "boot", "serve", "live", "tests", ".github", "docs")
SCANNED_FILES = ("Makefile", "pyproject.toml", "README.md", "CLAUDE.md")
# Records of past runs, not citations.
RECORDS = ("*last_run.txt",)
DECISIONS = "docs/decisions.md"
FRONT_PAGE_LINES = 60
ARCHIVED = re.compile(r"[0-9]{4}(?:-[a-z0-9-]+)?(?: design)? D[0-9]+|[0-9]{4}·D[0-9]+")
CITED = re.compile(r"\b[Dd]ecision (D[0-9]+)\b")
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
LINKED_DECISION = re.compile(r"decisions\.md#(d[0-9]+)\b")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
CODE = re.compile(r"`[^`\n]*`")
SPAN = re.compile(r"`([^`\n]+)`")
PATH = re.compile(r"[\w.-]+/[\w./{},*-]*(?:::[\w.]+)?")
# A file name holds a letter, so `127.0.0.1:8000` is an address, not a line.
LINE = re.compile(r"(?:[\w./-]*[A-Za-z][\w./-]*)?:\d+(?:-\d+)?")
# In prose, a dotted file and a line, not inside a URL: `see gpunit/x.py:12`.
PROSE_LINE = re.compile(r"(?<![\w./:-])[\w./-]+\.[A-Za-z]\w*:\d+(?:-\d+)?")


def guide(root: Path) -> list[Path]:
    """Return the pages whose links are held: `docs/`, `README.md` and `CLAUDE.md`."""
    pages = sorted((root / "docs").glob("*.md"))
    return pages + [root / name for name in ("README.md", "CLAUDE.md")]


def scanned(root: Path) -> dict[Path, str]:
    """Return each text file scanned for citations, with its text, records skipped."""
    found = [root / name for name in SCANNED_FILES]
    for top in SCANNED_DIRS:
        found += sorted(p for p in (root / top).rglob("*") if p.is_file())
    texts = {}
    for path in found:
        if not path.exists() or "__pycache__" in path.parts:
            continue
        if any(path.match(record) for record in RECORDS):
            continue
        try:
            texts[path] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
    return texts


def _prose(text: str) -> str:
    """Return `text` without its code blocks and spans, where a link is an example."""
    return CODE.sub("", FENCE.sub("", text))


def slug(heading: str) -> str:
    """Return a heading's GitHub anchor.

    e.g. "D22 · The host key" → "d22--the-host-key"
    """
    plain = re.sub(r"[`*]", "", heading).strip().lower()
    return re.sub(r"[^\w\- ]", "", plain).replace(" ", "-")


@functools.cache
def anchors(path: Path) -> set[str]:
    """Return every anchor the page's headings make, a repeat suffixed `-1`, `-2`."""
    seen: dict[str, int] = {}
    found = set()
    for line in FENCE.sub("", path.read_text(encoding="utf-8")).splitlines():
        if match := HEADING.match(line):
            base = slug(match[1])
            count = seen.get(base, 0)
            seen[base] = count + 1
            found.add(f"{base}-{count}" if count else base)
    return found


def broken_links(root: Path) -> list[str]:
    """Return each relative link in the guide naming a missing file or anchor."""
    faults = []
    for page in guide(root):
        if not page.exists():
            continue
        where = page.relative_to(root).as_posix()
        for target in LINK.findall(_prose(page.read_text(encoding="utf-8"))):
            if re.match(r"[a-z]+:", target):
                continue
            name, _, anchor = target.partition("#")
            path = (page.parent / name).resolve() if name else page
            if not path.exists() or (
                anchor and (path.suffix != ".md" or anchor not in anchors(path))
            ):
                faults.append(f"{where}: {target}")
    return sorted(faults)


def decision_ids(root: Path) -> set[str]:
    """Return the ids `docs/decisions.md` holds, from its `### Dn · ` headings."""
    text = (root / DECISIONS).read_text(encoding="utf-8")
    return set(re.findall(r"^### (D[0-9]+) · ", text, re.MULTILINE))


def unknown_decisions(root: Path) -> list[str]:
    """Return each `decision Dn` and decision link that names no decision in force."""
    known = decision_ids(root)
    faults = []
    for path, text in scanned(root).items():
        cited = CITED.findall(text) + [d.upper() for d in LINKED_DECISION.findall(text)]
        where = path.relative_to(root).as_posix()
        faults += [f"{where}: {d}" for d in set(cited) - known]
    return sorted(faults)


def archived(root: Path) -> list[str]:
    """Return each archived design's decision id cited outside `docs/decisions.md`."""
    faults = []
    for path, text in scanned(root).items():
        where = path.relative_to(root).as_posix()
        if where != DECISIONS:
            faults += [f"{where}: {cited}" for cited in ARCHIVED.findall(text)]
    return sorted(faults)


def tracked_tops(root: Path) -> set[str]:
    """Return the tracked top-level directories, e.g. {"gpunit", ".github"}."""
    listed = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.split()
    return {name.split("/")[0] for name in listed if "/" in name}


def _expand(path: str) -> list[str]:
    """Return `path` with its braces expanded.

    e.g. "x/{a,b}.py" → ["x/a.py", "x/b.py"]
    """
    if not (match := re.search(r"\{([^{}]*)\}", path)):
        return [path]
    return [
        found
        for part in match[1].split(",")
        for found in _expand(path[: match.start()] + part + path[match.end() :])
    ]


@functools.cache
def defined(path: Path) -> set[str]:
    """Return the names a module defines: functions, classes, assignments, `C.m`."""
    names = set()
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        if isinstance(node, ast.ClassDef):
            names |= {
                f"{node.name}.{sub.name}"
                for sub in node.body
                if isinstance(sub, ast.FunctionDef | ast.AsyncFunctionDef)
            }
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names |= {t.id for t in targets if isinstance(t, ast.Name)}
    return names


def unresolved(root: Path, tops: Collection[str]) -> list[str]:
    """Return each guide path, symbol or line citation that names nothing at `root`.

    e.g. `gpunit/lifecycle.py::up` passes while `up` is defined;
    `gpunit/lifecycle.py:75` is a line citation, and fails, in a span or in prose.
    """
    faults = []
    for page in sorted((root / "docs").glob("*.md")):
        where = page.relative_to(root).as_posix()
        text = FENCE.sub("", page.read_text(encoding="utf-8"))
        faults += [
            f"{where}: {line} cites a line"
            for line in PROSE_LINE.findall(CODE.sub("", text))
        ]
        for span in SPAN.findall(text):
            if LINE.fullmatch(span):
                faults.append(f"{where}: {span} cites a line")
                continue
            if not PATH.fullmatch(span):
                continue
            name, _, symbol = span.partition("::")
            if name.split("/")[0] not in tops:
                continue
            for path in _expand(name):
                found = list(root.glob(path)) if "*" in path else [root / path]
                if not any(p.exists() for p in found):
                    faults.append(f"{where}: {path} does not exist")
                elif symbol and symbol not in defined(found[0]):
                    faults.append(f"{where}: {path} defines no {symbol}")
    return sorted(faults)


def front_page(root: Path) -> list[str]:
    """Return why `README.md` is no front page: its length, or no usage link."""
    text = (root / "README.md").read_text(encoding="utf-8")
    faults = []
    if (length := len(text.splitlines())) > FRONT_PAGE_LINES:
        faults.append(f"README.md holds {length} lines, over {FRONT_PAGE_LINES}")
    links = {target.partition("#")[0] for target in LINK.findall(_prose(text))}
    if "docs/usage.md" not in links:
        faults.append("README.md links no docs/usage.md")
    return faults


@pytest.mark.spec("architecture:docs:links-resolve")
def test_the_guides_links_resolve() -> None:
    assert broken_links(ROOT) == []


@pytest.mark.spec("architecture:docs:link-caught")
def test_a_broken_link_is_caught(tmp_path: Path) -> None:
    root = tree(
        tmp_path,
        {
            "docs/a.md": (
                "[ok](b.md#d22--the-host-key) [ok](b.md#the-rules)"
                " [ok](b.md#the-rules-1) [ok](#a) [ok](../README.md) [web](https://example.com/x.md)\n"
                "[gone](missing.md) [none](b.md#nope) `[code](missing.md)`\n"
                '[ok](b.md "Title") [titled](gone.md "Title")\n'
                "```\n[fenced](missing.md)\n```\n# A\n"
            ),
            "docs/b.md": "### D22 · The host key\n## The rules\n## The rules\n",
            "README.md": "[here](docs/a.md#a) [there](docs/a.md#b)\n",
        },
    )

    assert broken_links(root) == [
        "README.md: docs/a.md#b",
        "docs/a.md: b.md#nope",
        "docs/a.md: gone.md",
        "docs/a.md: missing.md",
    ]


@pytest.mark.spec("architecture:docs:decisions-resolve")
def test_every_decision_cited_is_in_force() -> None:
    assert unknown_decisions(ROOT) == []


@pytest.mark.spec("architecture:docs:decisions-resolve")
def test_an_unknown_decision_is_caught(tmp_path: Path) -> None:
    # Joined, so this file cites no decision of its own.
    cite, link = "decision", "decisions.md#"
    root = tree(
        tmp_path,
        {
            DECISIONS: "### D1 · One\n\n### D2 · Two\n",
            "gpunit/x.py": f"# why: {cite} D1, {cite} D9\n",
            "docs/a.md": f"[one]({link}d2--two) [gone]({link}d7--gone)\n",
        },
    )

    assert unknown_decisions(root) == ["docs/a.md: D7", "gpunit/x.py: D9"]


@pytest.mark.spec("architecture:docs:archive-caught")
def test_no_archived_citation_is_left() -> None:
    assert archived(ROOT) == []


@pytest.mark.spec("architecture:docs:archive-caught")
def test_an_archived_citation_is_caught(tmp_path: Path) -> None:
    # Joined, so this file holds no citation of its own.
    cited = " ".join(["0010", "design", "D10"])
    named = " ".join(["0016-x", "design", "D3"])
    dotted = "·".join(["0014", "D4"])
    root = tree(
        tmp_path,
        {
            DECISIONS: f"- **Made by:** {cited}\n",
            "gpunit/x.py": f"# why: {cited}\n",
            "gpunit/y.py": f"# why: ({named}), {dotted}; not 0015·F23 or 0014·S1\n",
            "Makefile": f"# ({cited.replace('design ', '')})\n",
            "live/last_run.txt": f"{cited}\n",
        },
    )

    assert archived(root) == [
        f"Makefile: {cited.replace('design ', '')}",
        f"gpunit/x.py: {cited}",
        f"gpunit/y.py: {dotted}",
        f"gpunit/y.py: {named}",
    ]


@pytest.mark.spec("architecture:docs:symbols-resolve")
def test_the_guides_symbols_resolve() -> None:
    assert unresolved(ROOT, tracked_tops(ROOT)) == []


@pytest.mark.spec("architecture:docs:symbols-resolve")
def test_a_missing_symbol_or_a_line_citation_is_caught(tmp_path: Path) -> None:
    root = tree(
        tmp_path,
        {
            "gpunit/x.py": "N = 1\n\ndef up(): ...\n\nclass C:\n    def m(self): ...\n",
            "docs/a.md": (
                "`gpunit/x.py::up` `gpunit/x.py::N` `gpunit/x.py::C.m` `gpunit/*.py`"
                " `tests/test_<m>.py` `vllm/arg_utils.py` `127.0.0.1:8000`\n"
                "`gpunit/x.py::gone` `gpunit/{x,y}.py` `gpunit/x.py:75` `:12-14`\n"
                "`Makefile:12`, see gpunit/lifecycle.py:75, not 127.0.0.1:8000"
                " or https://example.com:8080/x\n"
                "```\n`gpunit/fenced.py`\ngpunit/fenced.py:3\n```\n"
            ),
        },
    )

    assert unresolved(root, {"gpunit", "tests"}) == [
        "docs/a.md: :12-14 cites a line",
        "docs/a.md: Makefile:12 cites a line",
        "docs/a.md: gpunit/lifecycle.py:75 cites a line",
        "docs/a.md: gpunit/x.py defines no gone",
        "docs/a.md: gpunit/x.py:75 cites a line",
        "docs/a.md: gpunit/y.py does not exist",
    ]


@pytest.mark.spec("architecture:readme:one-screen")
def test_the_front_page_fits_one_screen() -> None:
    assert front_page(ROOT) == []


@pytest.mark.spec("architecture:readme:one-screen")
def test_a_front_page_of_61_lines_is_caught(tmp_path: Path) -> None:
    # The twin: a line over is named with its length; no usage link is caught.
    long = tree(
        tmp_path / "long", {"README.md": "[usage](docs/usage.md)\n" + "x\n" * 60}
    )
    unlinked = tree(tmp_path / "unlinked", {"README.md": "`[usage](docs/usage.md)`\n"})

    assert front_page(long) == ["README.md holds 61 lines, over 60"]
    assert front_page(unlinked) == ["README.md links no docs/usage.md"]
