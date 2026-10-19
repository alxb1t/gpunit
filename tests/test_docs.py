"""Hold the guide's citations true: links, anchors and decision ids (decision D50)."""

import ast
import re
import subprocess
from collections.abc import Collection, Mapping
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# The roots scanned for citations: every tracked root but the specs and the archive.
SCANNED_DIRS = ("gpunit", "boot", "serve", "live", "tests", ".github", "docs")
SCANNED_FILES = ("Makefile", "pyproject.toml", "README.md", "CLAUDE.md")
DECISIONS = "docs/decisions.md"
ARCHIVED = re.compile(r"[0-9]{4} (design )?D[0-9]+")
CITED = re.compile(r"\b[Dd]ecision (D[0-9]+)\b")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
LINKED_DECISION = re.compile(r"decisions\.md#(d[0-9]+)\b")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
CODE = re.compile(r"`[^`\n]*`")
SPAN = re.compile(r"`([^`\n]+)`")
PATH = re.compile(r"[\w.-]+/[\w./{},*<>-]*(?:::[\w.]+)?")
LINE = re.compile(r"(?:[\w./-]+\.[A-Za-z]\w*|[\w./-]*Dockerfile[\w.]*)?:\d+(?:-\d+)?")


def guide(root: Path) -> list[Path]:
    """Return the pages whose links are held: `docs/`, `README.md` and `CLAUDE.md`."""
    pages = sorted((root / "docs").glob("*.md"))
    return pages + [root / name for name in ("README.md", "CLAUDE.md")]


def scanned(root: Path) -> list[Path]:
    """Return the text files scanned for citations; the live runs' tails are records."""
    found = [root / name for name in SCANNED_FILES]
    for top in SCANNED_DIRS:
        found += sorted(p for p in (root / top).rglob("*") if p.is_file())
    return [
        path
        for path in found
        if path.exists()
        and "__pycache__" not in path.parts
        and not path.name.endswith("last_run.txt")
        and _text(path) is not None
    ]


def _text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def _prose(text: str) -> str:
    """Return `text` without its code blocks and spans, where a link is an example."""
    return CODE.sub("", FENCE.sub("", text))


def slug(heading: str) -> str:
    """Return a heading's GitHub anchor.

    e.g. "D22 · The host key" → "d22--the-host-key"
    """
    plain = re.sub(r"[`*]", "", heading).strip().lower()
    return re.sub(r"[^\w\- ]", "", plain).replace(" ", "-")


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
            if not path.exists():
                faults.append(f"{where}: {target}")
            elif anchor and (path.suffix != ".md" or anchor not in anchors(path)):
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
    for path in scanned(root):
        text = path.read_text(encoding="utf-8")
        cited = CITED.findall(text) + [d.upper() for d in LINKED_DECISION.findall(text)]
        where = path.relative_to(root).as_posix()
        faults += [f"{where}: {d}" for d in set(cited) - known]
    return sorted(faults)


def archived(root: Path) -> list[str]:
    """Return each archived design's decision id cited outside `docs/decisions.md`."""
    faults = []
    for path in scanned(root):
        where = path.relative_to(root).as_posix()
        if where == DECISIONS:
            continue
        faults += [
            f"{where}: {m[0]}"
            for m in ARCHIVED.finditer(path.read_text(encoding="utf-8"))
        ]
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
    `gpunit/lifecycle.py:75` is a line citation, and fails.
    """
    faults = []
    for page in sorted((root / "docs").glob("*.md")):
        where = page.relative_to(root).as_posix()
        for span in SPAN.findall(FENCE.sub("", page.read_text(encoding="utf-8"))):
            if LINE.fullmatch(span):
                faults.append(f"{where}: {span} cites a line")
                continue
            if not PATH.fullmatch(span) or "<" in span:
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


def tree(root: Path, files: Mapping[str, str]) -> Path:
    """Write each file under `root`, by its relative path, and return `root`."""
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


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
                "```\n[fenced](missing.md)\n```\n# A\n"
            ),
            "docs/b.md": "### D22 · The host key\n## The rules\n## The rules\n",
            "README.md": "[here](docs/a.md#a) [there](docs/a.md#b)\n",
        },
    )

    assert broken_links(root) == [
        "README.md: docs/a.md#b",
        "docs/a.md: b.md#nope",
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
    root = tree(
        tmp_path,
        {
            DECISIONS: f"- **Made by:** {cited}\n",
            "gpunit/x.py": f"# why: {cited}\n",
            "Makefile": f"# ({cited.replace('design ', '')})\n",
            "live/last_run.txt": f"{cited}\n",
        },
    )

    assert archived(root) == [
        f"Makefile: {cited.replace('design ', '')}",
        f"gpunit/x.py: {cited}",
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
                "```\n`gpunit/fenced.py`\n```\n"
            ),
        },
    )

    assert unresolved(root, {"gpunit", "tests"}) == [
        "docs/a.md: :12-14 cites a line",
        "docs/a.md: gpunit/x.py defines no gone",
        "docs/a.md: gpunit/x.py:75 cites a line",
        "docs/a.md: gpunit/y.py does not exist",
    ]
