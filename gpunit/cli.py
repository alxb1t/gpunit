"""Parse the verbs, run one, and turn its outcome into the exit code."""

import argparse
import os
import sys
from pathlib import Path
from typing import NoReturn

from gpunit import log
from gpunit.spec import Spec, load_spec

USAGE = (
    "gpunit {up,status,down,ssh} [--spec PATH] | gpunit run [--spec PATH] -- <command>"
)

OK, FAILED, USAGE_FAULT, LOST = 0, 1, 2, 3


class Usage(Exception):
    """The command line is wrong; exit 2."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise Usage(message)


def _parser() -> _Parser:
    parser = _Parser(prog="gpunit")
    verbs = parser.add_subparsers(dest="verb", required=True, parser_class=_Parser)
    for verb in ("up", "status", "down", "ssh", "run"):
        sub = verbs.add_parser(verb)
        sub.add_argument("--spec", type=Path, default=Path("gpunit.toml"))
        if verb == "status":
            sub.add_argument("--json", action="store_true")
    return parser


def parse(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    """Return the parsed options and the command after `--`; raise `Usage` on a fault.

    e.g. ["run", "--", "echo", "hi"] → (Namespace(verb="run", ...), ["echo", "hi"])
    """
    # Split at `--` here: argparse's own `--` handling differs across 3.11–3.14.
    if "--" in argv:
        cut = argv.index("--")
        own, command = argv[:cut], argv[cut + 1 :]
    else:
        own, command = argv, None
    args = _parser().parse_args(own)
    if args.verb == "run" and not command:
        raise Usage("gpunit run -- <command> needs a command")
    if args.verb != "run" and command is not None:
        raise Usage(f"gpunit {args.verb} takes no command after --")
    if not args.spec.is_file() or not os.access(args.spec, os.R_OK):
        raise Usage(f"cannot read the spec {args.spec}")
    return args, command or []


def _not_built(args: argparse.Namespace, spec: Spec, command: list[str]) -> int:
    log.refuse(f"gpunit {args.verb} is not built yet")


VERBS = {verb: _not_built for verb in ("up", "status", "down", "ssh", "run")}


def main(argv: list[str] | None = None, *, provider: object | None = None) -> NoReturn:
    """Run one verb and exit: 0 done, 1 refused or failed, 2 usage, 3 lost."""
    sys.exit(_run(sys.argv[1:] if argv is None else argv, provider))


def _run(argv: list[str], provider: object | None) -> int:
    try:
        args, command = parse(argv)
    except Usage as fault:
        log.say(f"usage: {fault}")
        log.say(f"usage: {USAGE}")
        return USAGE_FAULT
    try:
        spec = load_spec(args.spec)
        return VERBS[args.verb](args, spec, command)
    except log.Refusal:
        return FAILED
