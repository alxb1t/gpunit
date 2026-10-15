"""Parse the verbs, run one, and turn its outcome into the exit code."""

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn

from gpunit import lifecycle, log, run
from gpunit.provider import Lost, Provider
from gpunit.runpod import RunPod
from gpunit.serve import table
from gpunit.spec import Spec, load_spec, parse_ceiling
from gpunit.state import State

USAGE = (
    "gpunit {up,status,down,ssh} [--spec PATH] | gpunit run [--spec PATH] -- <command>"
    " | gpunit serve <model> --ceiling 2h [--api] | gpunit down --serve <model>"
    " | gpunit spend [--days N] [--json]"
    " | gpunit volume up [--spec PATH | --serve <model> --ceiling 4h] [--yes]"
    " | gpunit volume down [--spec PATH | --serve <model>]"
)

FAILED, USAGE_FAULT = 1, 2
# Ten years: a window past any date the calendar can hold is refused, not a traceback.
DAYS, MAX_DAYS = 7, 3660


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
        if verb == "down":
            sub.add_argument("--serve", dest="model", metavar="MODEL")
    serve = verbs.add_parser("serve")
    serve.add_argument("model")
    serve.add_argument("--ceiling", type=_ceiling, required=True)
    serve.add_argument("--api", action="store_true")
    serve.add_argument("--volume")
    serve.add_argument("--max-hourly", type=float)
    serve.add_argument("--yes", action="store_true")
    serve.add_argument("--think", action="store_true")
    volume = verbs.add_parser("volume")
    actions = volume.add_subparsers(dest="action", required=True, parser_class=_Parser)
    for action in ("up", "down"):
        sub = actions.add_parser(action)
        sub.add_argument("--spec", type=Path, default=Path("gpunit.toml"))
        sub.add_argument("--serve", dest="model", metavar="MODEL")
        if action == "up":
            sub.add_argument("--ceiling", type=_ceiling)
            sub.add_argument("--yes", action="store_true")
    report = verbs.add_parser("spend")
    report.add_argument("--days", type=_days, default=DAYS)
    report.add_argument("--json", action="store_true")
    return parser


def _days(text: str) -> int:
    try:
        days = int(text)
    except ValueError:
        days = 0
    if not 1 <= days <= MAX_DAYS:
        raise argparse.ArgumentTypeError(
            f"{text!r} is not a whole number of days, from 1 to {MAX_DAYS}"
        )
    return days


def _ceiling(text: str) -> int:
    try:
        return parse_ceiling(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{text!r} is not a duration with a unit, as 600s, 45m or 4h"
        ) from None


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
    if getattr(args, "action", None) == "up":
        if args.model is not None and args.ceiling is None:
            raise Usage("gpunit volume up --serve <model> needs --ceiling")
        if args.model is None and args.ceiling is not None:
            raise Usage("--ceiling goes with --serve; a spec sets volume_ceiling")
    # `serve` and `--serve` name a model, whose spec is its table row;
    # `spend` has no `--spec`: it reads only the billing and the ledger.
    args.model = getattr(args, "model", None)
    if args.model is not None or not hasattr(args, "spec"):
        return args, []
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
        if args.model is not None:
            _known(args.model)
    except Usage as fault:
        log.say(f"usage: {fault}")
        log.say(f"usage: {USAGE}")
        return USAGE_FAULT
    except log.Refusal:
        return FAILED

    # Built only when a verb asks: no key is needed to read a spec or no record.
    def lazy() -> Provider:
        return provider or RunPod()

    state = State(Path.cwd())
    try:
        if args.model is not None:
            return _serve(args, lazy)
        if args.verb == "spend":
            # Here, not at the top: `decimal` would slow every other verb's start.
            from gpunit import spend

            return spend.spend(lazy(), args.days, as_json=args.json)
        spec = load_spec(args.spec)
        if args.verb == "volume":
            return _volume(args, spec, lazy(), state)
        match args.verb:
            case "up":
                lifecycle.up(spec, lazy(), state)
                return 0
            case "status":
                return lifecycle.status(lazy, state, as_json=args.json)
            case "down":
                return lifecycle.down(spec, lazy(), state)
            case "ssh":
                lifecycle.ssh(state)
                # unreachable: the exec replaces this process, or ssh() refuses
                return FAILED
            case _:
                return run.run(spec, lazy(), state, command)
    except log.Refusal:
        return FAILED
    except Lost:
        return run.LOST_EXIT


def _serve(args: argparse.Namespace, provider: Callable[[], Provider]) -> int:
    # Here, not at the top: its imports would slow every other verb's start.
    from gpunit.serve import session

    if args.verb == "down":
        return session.down(args.model, provider())
    if args.verb == "volume":
        if args.action == "up":
            return session.volume_up(
                args.model, args.ceiling, yes=args.yes, provider=provider()
            )
        return session.volume_down(args.model, provider())
    return session.serve(
        args.model,
        args.ceiling,
        api=args.api,
        volume=args.volume,
        max_hourly=args.max_hourly,
        yes=args.yes,
        think=args.think,
        provider=provider(),
    )


def _volume(
    args: argparse.Namespace, spec: Spec, provider: Provider, state: State
) -> int:
    # Here, not at the top: `decimal` would slow every other verb's start.
    from gpunit import volume

    if args.action == "up":
        return volume.up(spec, provider, state, yes=args.yes)
    return volume.down(spec, provider, state)


def _known(model: str) -> None:
    models = sorted(table.load().models)
    if model not in models:
        raise Usage(f"no model {model!r} in the table; it holds {', '.join(models)}")
