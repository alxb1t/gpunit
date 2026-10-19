"""Hold the package to its layers: imports point down, per decision D49."""

import ast
import sys
from collections.abc import Collection, Mapping
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# A new module edits this table and `docs/modules.md` together.
LAYERS = {
    "gpunit": "interface",
    "gpunit.__main__": "interface",
    "gpunit.cli": "interface",
    "gpunit.serve": "serve",
    "gpunit.serve.table": "serve",
    "gpunit.serve.chat": "serve",
    "gpunit.serve.session": "serve",
    "gpunit.library": "session",
    "gpunit.run": "session",
    "gpunit.lifecycle": "lifecycle",
    "gpunit.volume": "lifecycle",
    "gpunit.spend": "lifecycle",
    "gpunit.runpod": "cloud",
    "gpunit.spec": "model",
    "gpunit.state": "model",
    "gpunit.provider": "model",
    "gpunit.ledger": "model",
    "gpunit.log": "foundation",
    "gpunit.version": "foundation",
}
RANK = {
    layer: rank
    for rank, layer in enumerate(
        ["foundation", "model", "cloud", "lifecycle", "session", "serve", "interface"]
    )
}
BUILDERS = {"gpunit.library", "gpunit.cli"}


def modules(root: Path) -> dict[str, Path]:
    """Return each module of the package under `root`, by dotted name.

    e.g. gpunit/serve/table.py → gpunit.serve.table, gpunit/__init__.py → gpunit
    """
    found = {}
    for path in sorted((root / "gpunit").rglob("*.py")):
        parts = path.relative_to(root).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        found[".".join(parts)] = path
    return found


def imports(path: Path, names: Collection[str]) -> list[tuple[int, str]]:
    """Return each line and module the file imports, those inside functions included.

    A `from` import of a module in `names` names that module: `from gpunit import log`
    → gpunit.log, and `from gpunit import __version__` → gpunit.
    """
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                child = f"{node.module}.{alias.name}"
                found.append((node.lineno, child if child in names else node.module))
    return sorted(found)


def upward(root: Path, layers: Mapping[str, str] = LAYERS) -> list[str]:
    """Return each import that names a higher layer or the package itself."""
    found = modules(root)
    faults = []
    for name, path in found.items():
        if name not in layers:
            faults.append(f"{name}: no layer")
            continue
        for line, target in imports(path, found):
            if target == "gpunit":
                faults.append(f"{name}:{line} imports gpunit itself")
            elif target in layers and RANK[layers[target]] > RANK[layers[name]]:
                faults.append(f"{name}:{line} imports {target}")
    return faults


def cycles(root: Path) -> list[str]:
    """Return each import cycle among the package's modules, e.g. a → b → a."""
    found = modules(root)
    graph = {
        name: sorted({t for _, t in imports(path, found) if t in found and t != name})
        for name, path in found.items()
    }
    faults: list[str] = []
    done: set[str] = set()

    def visit(name: str, trail: list[str]) -> None:
        if name in trail:
            faults.append(" → ".join([*trail[trail.index(name) :], name]))
        elif name not in done:
            for target in graph[name]:
                visit(target, [*trail, name])
            done.add(name)

    for name in graph:
        visit(name, [])
    return faults


def importers(root: Path, module: str) -> set[str]:
    """Return the package's modules that import `module`."""
    found = modules(root)
    return {
        name
        for name, path in found.items()
        if any(target == module for _, target in imports(path, found))
    }


def foreign(root: Path) -> list[str]:
    """Return each import in the package or the launcher not of the stdlib or gpunit."""
    found = modules(root)
    faults = []
    for path in [*found.values(), root / "serve" / "launch.py"]:
        if not path.exists():
            continue
        for line, target in imports(path, found):
            top = target.partition(".")[0]
            if top != "gpunit" and top not in sys.stdlib_module_names:
                faults.append(
                    f"{path.relative_to(root).as_posix()}:{line} imports {target}"
                )
    return faults


def exits(root: Path) -> list[str]:
    """Return each `sys.exit` the package calls outside `gpunit/cli.py`."""
    faults = []
    for path in modules(root).values():
        where = path.relative_to(root).as_posix()
        if where == "gpunit/cli.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module == "sys":
                bound = [alias.name for alias in node.names if alias.name == "exit"]
                faults += [f"{where}:{node.lineno} imports sys.exit" for _ in bound]
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and (node.func.value.id, node.func.attr) == ("sys", "exit")
            ):
                faults.append(f"{where}:{node.lineno} calls sys.exit")
    return faults


def package(root: Path, files: Mapping[str, str]) -> Path:
    """Write a small package under `root`, each file by its relative path."""
    for name, source in {"gpunit/__init__.py": "", **files}.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return root


@pytest.mark.spec("architecture:layers:hold")
def test_the_package_holds_its_layers() -> None:
    assert upward(ROOT) == []
    assert cycles(ROOT) == []


@pytest.mark.spec("architecture:layers:upward-caught")
@pytest.mark.parametrize(
    ("files", "faults"),
    [
        (
            {"gpunit/spec.py": "from gpunit import lifecycle\n"},
            ["gpunit.spec:1 imports gpunit.lifecycle"],
        ),
        (
            {"gpunit/spec.py": "def load():\n    import gpunit.lifecycle\n"},
            ["gpunit.spec:2 imports gpunit.lifecycle"],
        ),
        (
            {"gpunit/spec.py": "from gpunit import __version__\n"},
            ["gpunit.spec:1 imports gpunit itself"],
        ),
        ({"gpunit/extra.py": ""}, ["gpunit.extra: no layer"]),
    ],
)
def test_an_upward_import_is_caught(
    tmp_path: Path, files: dict[str, str], faults: list[str]
) -> None:
    root = package(tmp_path, {"gpunit/lifecycle.py": "", **files})

    assert upward(root) == faults


@pytest.mark.spec("architecture:layers:cycle-caught")
def test_a_cycle_is_caught(tmp_path: Path) -> None:
    root = package(
        tmp_path,
        {
            "gpunit/spec.py": "from gpunit import state\n",
            "gpunit/state.py": "def load():\n    from gpunit import spec\n",
        },
    )

    assert upward(root) == []
    assert cycles(root) == ["gpunit.spec → gpunit.state → gpunit.spec"]


@pytest.mark.spec("architecture:layers:provider-built")
def test_runpod_is_built_in_library_and_cli_alone() -> None:
    assert importers(ROOT, "gpunit.runpod") == BUILDERS


@pytest.mark.spec("architecture:layers:provider-built")
def test_a_third_runpod_importer_is_caught(tmp_path: Path) -> None:
    root = package(
        tmp_path,
        {
            "gpunit/runpod.py": "",
            "gpunit/library.py": "from gpunit.runpod import RunPod\n",
            "gpunit/cli.py": "from gpunit.runpod import RunPod\n",
            "gpunit/run.py": "def go():\n    from gpunit import runpod\n",
        },
    )

    assert importers(root, "gpunit.runpod") - BUILDERS == {"gpunit.run"}


@pytest.mark.spec("architecture:layers:stdlib-only")
def test_the_package_imports_the_stdlib_alone() -> None:
    assert foreign(ROOT) == []


@pytest.mark.spec("architecture:layers:stdlib-only")
def test_a_foreign_import_is_caught(tmp_path: Path) -> None:
    root = package(
        tmp_path,
        {
            "gpunit/log.py": "import os\nimport requests\n",
            "gpunit/spec.py": "def load():\n    from tests import fakes\n",
            "gpunit/state.py": "import boot.boot\nfrom live import window\n",
            "serve/launch.py": "import os\nimport vllm\n",
        },
    )

    assert foreign(root) == [
        "gpunit/log.py:2 imports requests",
        "gpunit/spec.py:2 imports tests",
        "gpunit/state.py:1 imports boot.boot",
        "gpunit/state.py:2 imports live",
        "serve/launch.py:2 imports vllm",
    ]


@pytest.mark.spec("architecture:layers:exit-in-cli")
def test_only_the_cli_exits() -> None:
    assert exits(ROOT) == []


@pytest.mark.spec("architecture:layers:exit-in-cli")
def test_an_exit_outside_the_cli_is_caught(tmp_path: Path) -> None:
    root = package(
        tmp_path,
        {
            "gpunit/cli.py": "import sys\nsys.exit(0)\n",
            "gpunit/volume.py": "import sys\n\ndef up():\n    sys.exit(1)\n",
            "gpunit/spend.py": "from sys import exit\n",
        },
    )

    assert exits(root) == [
        "gpunit/spend.py:1 imports sys.exit",
        "gpunit/volume.py:4 calls sys.exit",
    ]
