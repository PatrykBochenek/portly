"""Typed exception hierarchy for portly.

The native extension raises builtin exceptions (``OSError`` /
``PermissionError`` via PyO3). The public API re-raises them as this
hierarchy, which also subclasses the builtins so existing ``except
OSError`` / ``except PermissionError`` handlers keep working.
"""


class PortlyError(Exception):
    """Base class for all portly errors."""


class PortlyPortError(PortlyError, OSError):
    """A port-related failure (invalid port, no free port found).

    Also a subclass of :class:`OSError`, so existing ``except OSError``
    handlers keep working.
    """


class PortlyPermissionError(PortlyError, PermissionError):
    """Permission denied while inspecting or killing a process.

    Also a subclass of :class:`PermissionError`, so existing
    ``except PermissionError`` handlers keep working.
    """
