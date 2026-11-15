"""Argument validation for the public portly API.

The native extension takes ``u16``/``u64`` parameters; values outside
those ranges would surface as raw ``OverflowError``/``TypeError`` from
PyO3. These helpers reject bad arguments up front with typed
``PortlyPortError`` exceptions instead.
"""

from portly._errors import PortlyPortError

_PORT_MIN = 1
_PORT_MAX = 65535
_TIMEOUT_MAX = 2**64 - 1


def _validate_port(port: int, name: str = "port") -> int:
    """Return *port* if it fits the 0-65535 range, else raise PortlyPortError.

    Single-port functions preserve their existing port 0 behavior (e.g.
    ``find_free(0)`` returns any free port, ``kill(0)`` is a no-op that
    reports success), so it is accepted like any other valid port.
    """
    if not isinstance(port, int):
        raise PortlyPortError(
            f"{name} must be an integer port number ({_PORT_MIN}-{_PORT_MAX}), "
            f"got {type(port).__name__}"
        )
    if not 0 <= port <= _PORT_MAX:
        raise PortlyPortError(f"{name} must be between {_PORT_MIN} and {_PORT_MAX}, got {port}")
    return port


def _validate_timeout(timeout: int, name: str = "timeout") -> int:
    """Return *timeout* if it is a non-negative integer, else raise."""
    if not isinstance(timeout, int):
        raise PortlyPortError(
            f"{name} must be an integer number of seconds >= 0, got {type(timeout).__name__}"
        )
    if not 0 <= timeout <= _TIMEOUT_MAX:
        raise PortlyPortError(f"{name} must be between 0 and {_TIMEOUT_MAX} seconds, got {timeout}")
    return timeout


def _validate_range(lo: int, hi: int, count: int) -> None:
    """Validate find_free_in_range arguments, preserving its ValueError contract."""
    for name, value in (("lo", lo), ("hi", hi), ("count", count)):
        if not isinstance(value, int):
            raise PortlyPortError(f"{name} must be an integer, got {type(value).__name__}")
    # Structural range errors keep raising ValueError (documented and
    # backwards-compatible), while numeric overflow becomes PortlyPortError.
    if lo == 0:
        raise ValueError("lo must be >= 1 (port 0 is not a valid lower bound)")
    for name, value in (("lo", lo), ("hi", hi)):
        if not _PORT_MIN <= value <= _PORT_MAX:
            raise PortlyPortError(
                f"{name} must be between {_PORT_MIN} and {_PORT_MAX}, got {value}"
            )
    if lo > hi:
        raise ValueError(f"lo ({lo}) must be <= hi ({hi})")
    if not 0 <= count <= _PORT_MAX:
        raise PortlyPortError(f"count must be between 0 and {_PORT_MAX}, got {count}")
