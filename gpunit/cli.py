"""Parse the verbs, run one, and turn its outcome into the exit code."""

import argparse
import os
import sys
from pathlib import Path
from typing import NoReturn

from gpunit import log, run, session
from gpunit.provider import Lost, Provider
from gpunit.runpod import RunPod
from gpunit.spec import load_spec
from gpunit.state import State

USAGE = (
    "gpunit {up,status,down,ssh} [--spec PATH] | gpunit run [--spec PATH] -- <command>"
)

FAILED, USAGE_FAULT = 1, 2


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


def main(
    argv: list[str] | None = None, *, provider: Provider | None = None
) -> NoReturn:
    """Run one verb and exit: 0 done, 1 refused or failed, 2 usage, 3 lost."""
    sys.exit(_run(sys.argv[1:] if argv is None else argv, provider))


def _run(argv: list[str], provider: Provider | None) -> int:
    try:
        args, command = parse(argv)
    except Usage as fault:
        log.say(f"usage: {fault}")
        log.say(f"usage: {USAGE}")
        return USAGE_FAULT

    # Built only when a verb asks: no key is needed to read a spec or no record.
    def lazy() -> Provider:
        return provider or RunPod()

    state = State(Path.cwd())
    try:
        spec = load_spec(args.spec)
        match args.verb:
            case "up":
                session.up(spec, lazy(), state)
                return 0
            case "status":
                return session.status(lazy, state, as_json=args.json)
            case "down":
                return session.down(spec, lazy(), state)
            case "ssh":
                session.ssh(state)
                return FAILED  # reached only when the exec failed
            case _:
                return run.run(spec, lazy(), state, command)
    except log.Refusal:
        return FAILED
    except Lost:
        return run.LOST_EXIT
