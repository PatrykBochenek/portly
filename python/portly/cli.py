"""portly — command-line interface.

A small, dependency-free CLI built on :mod:`argparse` that wraps the
:mod:`portly` library. Run ``portly --help`` for usage.
"""

from __future__ import annotations

import argparse
import errno
import io
import json
import os
import sys
from collections.abc import Callable
from typing import Any, cast

import portly
from portly import PortlyError, PortlyPermissionError, PortlyPortError

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_INTERRUPT = 130

_EPILOG = (
    "exit codes: 0 success, 1 negative result or failure, 2 usage error, 130 interrupted (Ctrl-C)"
)


def _port_type(value: str) -> int:
    """Parse a port number, rejecting anything outside 1..65535."""
    if not value.isdigit():
        raise argparse.ArgumentTypeError(f"invalid port: {value!r}")
    port = int(value)
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"port must be between 1 and 65535, got {port}")
    return port


def _timeout_type(value: str) -> int:
    """Parse a non-negative timeout in seconds."""
    if not value.isdigit():
        raise argparse.ArgumentTypeError(f"invalid timeout: {value!r}")
    timeout = int(value)
    if timeout < 0:
        raise argparse.ArgumentTypeError("timeout must be >= 0")
    return timeout


def _print_json(data: Any) -> None:
    """Print *data* as a single JSON line on stdout."""
    print(json.dumps(data))


def _error(message: str) -> None:
    """Print *message* on stderr."""
    print(message, file=sys.stderr)


def _cmd_check(args: argparse.Namespace, json_out: bool) -> int:
    available = portly.is_available(args.port)
    if json_out:
        _print_json({"port": args.port, "available": available})
    else:
        status = "available" if available else "in use"
        print(f"port {args.port} is {status}")
    return EXIT_OK if available else EXIT_FAILURE


def _cmd_find(args: argparse.Namespace, json_out: bool) -> int:
    try:
        port = portly.find_free(args.preferred)
    except PortlyPortError as exc:
        _error(f"no free port found: {exc}")
        return EXIT_FAILURE
    if json_out:
        _print_json({"port": port})
    else:
        print(port)
    return EXIT_OK


def _cmd_scan(args: argparse.Namespace, json_out: bool) -> int:
    results = portly.scan(args.ports)
    if json_out:
        _print_json({str(port): results[port] for port in args.ports})
    else:
        for port in args.ports:
            info = results[port]
            if info is None:
                if portly.is_available(port):
                    print(f"{port}: free")
                else:
                    print(f"{port}: in use (owner not visible)")
            else:
                print(f"{port}: in use (pid={info['pid']}, name={info['name']})")
    return EXIT_OK


def _cmd_info(args: argparse.Namespace, json_out: bool) -> int:
    info = portly.get_info(args.port)
    if info is not None:
        if json_out:
            _print_json({"port": args.port, "info": info})
        else:
            print(f"pid: {info['pid']}")
            print(f"name: {info['name']}")
            print(f"cmd: {info['cmd']}")
        return EXIT_OK
    if portly.is_available(args.port):
        if json_out:
            _print_json({"port": args.port, "info": None})
        else:
            print(f"port {args.port} is free")
        return EXIT_FAILURE
    if json_out:
        _print_json({"port": args.port, "info": None})
    else:
        print(f"port {args.port} is in use (owner not visible)")
    return EXIT_OK


def _cmd_kill(args: argparse.Namespace, json_out: bool) -> int:
    try:
        killed = portly.kill(args.port, force=args.force)
    except PortlyPermissionError as exc:
        _error(f"permission denied killing process on port {args.port}: {exc}")
        return EXIT_FAILURE
    except PortlyPortError as exc:
        _error(f"could not kill process on port {args.port}: {exc}")
        return EXIT_FAILURE
    except PortlyError as exc:
        _error(f"could not kill process on port {args.port}: {exc}")
        return EXIT_FAILURE
    if json_out:
        _print_json({"port": args.port, "killed": killed})
    else:
        message = f"port {args.port} is free" if killed else f"port {args.port} is still in use"
        print(message)
    return EXIT_OK if killed else EXIT_FAILURE


def _cmd_wait(args: argparse.Namespace, json_out: bool) -> int:
    free = portly.wait_until_free(args.port, timeout=args.timeout)
    if json_out:
        _print_json({"port": args.port, "free": free})
    elif free:
        print(f"port {args.port} is free")
    else:
        _error(f"port {args.port} is still in use after {args.timeout}s")
    return EXIT_OK if free else EXIT_FAILURE


def _cmd_wait_for_server(args: argparse.Namespace, json_out: bool) -> int:
    accepting = portly.wait_for_server(args.port, timeout=args.timeout)
    if json_out:
        _print_json({"port": args.port, "accepting": accepting})
    elif accepting:
        print(f"port {args.port} is accepting connections")
    else:
        _error(f"port {args.port} is not accepting connections after {args.timeout}s")
    return EXIT_OK if accepting else EXIT_FAILURE


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    """Add a ``--json`` flag that only sets a value when given.

    ``default=argparse.SUPPRESS`` keeps the subcommand flag from clobbering
    the global one when both are accepted.
    """
    parser.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="print machine-readable JSON to stdout",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the :mod:`argparse` parser for the ``portly`` command."""
    parser = argparse.ArgumentParser(
        prog="portly",
        description="Inspect, scan and free TCP/UDP ports.",
        epilog=_EPILOG,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {portly.__version__}")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON to stdout")

    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    check = sub.add_parser("check", help="check whether a port is available")
    _add_json_flag(check)
    check.add_argument("port", type=_port_type, help="port number (1-65535)")
    check.set_defaults(func=_cmd_check)

    find = sub.add_parser("find", help="print a free port")
    _add_json_flag(find)
    find.add_argument("--preferred", type=_port_type, default=None, help="prefer this port if free")
    find.set_defaults(func=_cmd_find)

    scan = sub.add_parser("scan", help="report status for one or more ports")
    _add_json_flag(scan)
    scan.add_argument(
        "ports", type=_port_type, nargs="+", metavar="PORT", help="port numbers (1-65535)"
    )
    scan.set_defaults(func=_cmd_scan)

    info = sub.add_parser("info", help="show process info for a port")
    _add_json_flag(info)
    info.add_argument("port", type=_port_type, help="port number (1-65535)")
    info.set_defaults(func=_cmd_info)

    kill = sub.add_parser("kill", help="kill the process using a port")
    _add_json_flag(kill)
    kill.add_argument("port", type=_port_type, help="port number (1-65535)")
    kill.add_argument("--force", action="store_true", help="kill forcefully (SIGKILL)")
    kill.set_defaults(func=_cmd_kill)

    wait = sub.add_parser("wait", help="wait until a port is free")
    _add_json_flag(wait)
    wait.add_argument("port", type=_port_type, help="port number (1-65535)")
    wait.add_argument(
        "--timeout", type=_timeout_type, default=30, help="seconds to wait (default: 30)"
    )
    wait.set_defaults(func=_cmd_wait)

    wait_for_server = sub.add_parser(
        "wait-for-server", help="wait until a port accepts connections"
    )
    _add_json_flag(wait_for_server)
    wait_for_server.add_argument("port", type=_port_type, help="port number (1-65535)")
    wait_for_server.add_argument(
        "--timeout", type=_timeout_type, default=30, help="seconds to wait (default: 30)"
    )
    wait_for_server.set_defaults(func=_cmd_wait_for_server)

    return parser


def _redirect_stdout_to_devnull() -> None:
    """Redirect stdout's file descriptor to the null device."""
    try:
        stdout_fd = sys.stdout.fileno()
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(devnull_fd, stdout_fd)
        finally:
            os.close(devnull_fd)
    except (OSError, ValueError):
        # Replace stdout before closing it: close may fail while flushing, but
        # shutdown will then flush only this in-memory stream.
        broken_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            broken_stdout.close()
        except (OSError, ValueError):
            return


def _flush_stdout() -> None:
    """Normalize Windows' closed-pipe flush error for the existing cleanup path."""
    try:
        sys.stdout.flush()
    except OSError as exc:
        # Windows can report ERROR_NO_DATA as EINVAL when a pipe's reader has
        # already closed. Keep this workaround scoped to stdout flushing:
        # an EINVAL from a command handler is not evidence of a broken pipe.
        # https://github.com/python/cpython/issues/79935
        if sys.platform == "win32" and exc.errno == errno.EINVAL:
            raise BrokenPipeError(errno.EPIPE, "stdout pipe closed") from exc
        raise


def main(argv: list[str] | None = None) -> int:
    """Run the ``portly`` CLI; returns the process exit code."""
    parser = build_parser()
    try:
        try:
            args = parser.parse_args(argv)
        except SystemExit:
            _flush_stdout()
            raise
    except BrokenPipeError:
        _redirect_stdout_to_devnull()
        return EXIT_FAILURE

    json_out = bool(getattr(args, "json", False))
    handler = cast(Callable[[argparse.Namespace, bool], int], vars(args)["func"])
    try:
        result = handler(args, json_out)
    except KeyboardInterrupt:
        _error("interrupted")
        result = EXIT_INTERRUPT
    except BrokenPipeError:
        _redirect_stdout_to_devnull()
        return EXIT_FAILURE
    except PortlyError as exc:
        _error(str(exc))
        result = EXIT_FAILURE

    try:
        _flush_stdout()
    except BrokenPipeError:
        _redirect_stdout_to_devnull()
        return EXIT_FAILURE
    return result


if __name__ == "__main__":
    sys.exit(main())
