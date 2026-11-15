"""portly — cross-platform Python port management made simple.

A Rust-powered library to inspect, scan and free TCP/UDP ports.

Example:
    >>> import portly as pw
    >>> pw.is_available(8000)
    True
    >>> port = pw.find_free(8000)
    >>> pw.wait_until_free(5432, timeout=30)
    True
"""

# The native extension exposes the raw functions. The public API below wraps
# them so failures surface as the typed `PortlyError` hierarchy instead of
# bare builtin exceptions (while staying compatible with `except OSError` /
# `except PermissionError`).
from portly import _lib
from portly._errors import PortlyError, PortlyPermissionError, PortlyPortError
from portly._lib import __version__ as __version__
from portly._validation import _validate_port, _validate_range, _validate_timeout

__all__ = [
    "PortlyError",
    "PortlyPermissionError",
    "PortlyPortError",
    "__version__",
    "find_free",
    "find_free_in_range",
    "get_info",
    "is_available",
    "kill",
    "scan",
    "wait_for_server",
    "wait_until_free",
]


def is_available(port: int) -> bool:
    """Return True if *port* is free on localhost, False otherwise."""
    return _lib.is_available(_validate_port(port))


def find_free(preferred: int | None = None) -> int:
    """Return a free port, preferring *preferred* when it is free.

    Raises:
        PortlyPortError: If no free port could be found.
    """
    if preferred is not None:
        preferred = _validate_port(preferred, "preferred")
    try:
        return _lib.find_free(preferred)
    except OSError as exc:
        raise PortlyPortError(str(exc)) from exc


def find_free_in_range(lo: int = 1024, hi: int = 65535, count: int = 1) -> int | list[int]:
    """Return free port(s) within the inclusive range ``[lo, hi]``.

    Returns a single port number when *count* is 1, otherwise a list of
    distinct free ports.

    Raises:
        ValueError: If *lo* == 0 or *lo* > *hi*.
        PortlyPortError: If fewer than *count* free ports exist in the range.
    """
    _validate_range(lo, hi, count)
    try:
        return _lib.find_free_in_range(lo, hi, count)
    except ValueError:
        raise
    except OSError as exc:
        raise PortlyPortError(str(exc)) from exc


def wait_until_free(port: int, timeout: int = 30) -> bool:
    """Wait up to *timeout* seconds for *port* to become free.

    Returns True if the port became free, False on timeout.
    """
    return _lib.wait_until_free(
        _validate_port(port),
        _validate_timeout(timeout),
    )


def wait_for_server(
    port: int, host: str = "127.0.0.1", timeout: int = 30, interval: float = 0.1
) -> bool:
    """Wait up to *timeout* seconds for a server to accept connections on *port*.

    Polls *host*:*port* with TCP connect attempts every *interval* seconds.
    Returns True once the port accepts a connection, False on timeout.
    """
    return _lib.wait_for_server(_validate_port(port), host, _validate_timeout(timeout), interval)


def get_info(port: int) -> dict[str, int | str] | None:
    """Return information about the process listening on *port*.

    Returns None if the port is free (or its owner is not visible to us).
    """
    return _lib.get_info(_validate_port(port))


def kill(port: int, force: bool = False) -> bool:
    """Kill the process(es) using *port*.

    Sends SIGTERM unless *force* is True (SIGKILL on Unix; TerminateProcess
    on Windows regardless of *force*). Returns True if the port became free.

    Raises:
        PortlyPermissionError: If we lack permission to kill the process.
        PortlyPortError: If the process(es) could not be killed for another
            reason.
    """
    port = _validate_port(port)
    try:
        return _lib.kill(port, force)
    except PermissionError as exc:
        raise PortlyPermissionError(str(exc)) from exc
    except OSError as exc:
        raise PortlyPortError(str(exc)) from exc


def scan(ports: list[int]) -> dict[int, dict[str, int | str] | None]:
    """Return process info for each port in *ports* (None when free)."""
    return _lib.scan([_validate_port(p) for p in ports])
