# gpunit — coding standards

The rules this repo's code follows. Mandatory context, named by [AGENTS.md](AGENTS.md).

## Baseline

The MinionsFactory `mf-build` skill's rules apply as written: comments `C1`…`C12`, tests `T1`…`T6`, prose
`P1`…`P13`. Formatter and linter settings stay in their own config files.

## Project rules

The package, `boot/boot.py` and `serve/launch.py` use the standard library alone
(`tests/test_layers.py::test_the_package_imports_the_stdlib_alone`, `tests/test_boot.py::test_boot_runs_on_the_stdlib_alone`).
`boot/boot.py` runs on the pod's Python 3.10, and the gate holds it at full line and branch coverage. Prose names the
things it means and counts none.

The rules the code follows, each with the test that holds it, are in [principles](docs/principles.md); a rule there
that names a C rule replaces it.
