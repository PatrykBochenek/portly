from portly._lib import PortInfo as PortInfo
from portly._lib import __version__ as __version__

class PortlyError(Exception):
    """Base class for all portly errors."""

class PortlyPortError(PortlyError, OSError):
    """A port-related failure (invalid port, no free port found)."""

class PortlyPermissionError(PortlyError, PermissionError):
    """Permission denied while inspecting or killing a process."""

def is_available(port: int) -> bool:
    """Return True if *port* is free on localhost, False otherwise."""
    ...

def find_free(preferred: int | None = None) -> int:
    """Return a free port, preferring *preferred* when it is free.

    Raises:
        PortlyPortError: If no free port could be found.
    """
    ...

def find_free_in_range(lo: int = 1024, hi: int = 65535, count: int = 1) -> int | list[int]:
    """Return free port(s) within the inclusive range ``[lo, hi]``.

    Returns a single port number when *count* is 1, otherwise a list of
    distinct free ports.

    Raises:
        ValueError: If *lo* == 0 or *lo* > *hi*.
        PortlyPortError: If fewer than *count* free ports exist in the range.
    """
    ...

def wait_until_free(port: int, timeout: int = 30) -> bool:
    """Wait up to *timeout* seconds for *port* to become free."""
    ...

def wait_for_server(
    port: int, host: str = "127.0.0.1", timeout: int = 30, interval: float = 0.1
) -> bool:
    """Wait up to *timeout* seconds for a server to accept on *port*."""
    ...

def get_info(port: int) -> PortInfo | None:
    """Return information about the process listening on *port*."""
    ...

def kill(port: int, force: bool = False) -> bool:
    """Kill the process(es) using *port*.

    Raises:
        PortlyPermissionError: If we lack permission to kill the process.
        PortlyPortError: If the process(es) could not be killed for another
            reason.
    """
    ...

def scan(ports: list[int]) -> dict[int, PortInfo | None]:
    """Return process info for each port in *ports* (None when free)."""
    ...

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
