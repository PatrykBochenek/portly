<div align="center">

# portly

**Cross-platform Python port management made simple.**

[![PyPI version](https://img.shields.io/pypi/v/portly?cacheSeconds=3600)](https://pypi.org/project/portly/)
[![Python versions](https://img.shields.io/pypi/pyversions/portly?cacheSeconds=3600)](https://pypi.org/project/portly/)
[![License](https://img.shields.io/pypi/l/portly?cacheSeconds=3600)](https://github.com/PatrykBochenek/portly/blob/main/LICENSE)
[![CI](https://github.com/PatrykBochenek/portly/actions/workflows/CI.yml/badge.svg)](https://github.com/PatrykBochenek/portly/actions/workflows/CI.yml)
[![codecov](https://codecov.io/gh/PatrykBochenek/portly/branch/main/graph/badge.svg)](https://codecov.io/gh/PatrykBochenek/portly)
[![Docs](https://img.shields.io/badge/docs-mkdocs-4b8bbe)](https://patrykbochenek.github.io/portly/)
[![Typed](https://img.shields.io/badge/typing-typed-4b8bbe)](https://github.com/PatrykBochenek/portly/blob/main/python/portly/py.typed)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

<img src="docs/portly.png" alt="portly" width="340">

</div>

Check whether a port is free, find a free port, wait for one to become free,
inspect what is listening on it, scan a list of ports, or kill whatever is
holding one — fast, and on Linux, macOS, and Windows.

Everything is implemented natively (no `lsof`, `netstat`, `wmic`, or other
subprocesses), so it works in minimal containers and is safe from shell
escaping issues.

## Installation

```bash
pip install portly
```

Requires Python 3.10+. Pre-built wheels are available for Linux (manylinux &
musllinux), macOS (Intel & Apple Silicon), and Windows (x64 & arm64).

## Quick Start

```python
import portly

# Check if a port is available
if portly.is_available(8000):
    print("Port 8000 is free!")

# Find a free port (preferring 8000 if it happens to be free)
port = portly.find_free(8000)

# Wait for a port to become free (up to 30s)
portly.wait_until_free(5432, timeout=30)

# Kill the process using a port
portly.kill(8000)

# Get process info
info = portly.get_info(8000)
# {'pid': 1234, 'name': 'python', 'cmd': 'python app.py'}  (or None)

# Scan multiple ports at once
results = portly.scan([8000, 8001, 5432])
```

## Command Line

Installing the package also provides a `portly` command for terminal use:

```bash
portly check 8000              # is the port free? (exit 0 = yes, 1 = in use)
portly find                    # print a free port
portly find --preferred 8000   # prefer 8000 if it happens to be free
portly scan 8000 8001 5432     # per-port status
portly info 8000               # pid/name/cmd of the process using the port
portly kill 8000               # free the port (add --force for SIGKILL)
portly wait 8000 --timeout 30  # wait until the port is free
portly wait-for-server 8000    # wait until a server accepts connections
```

Add `--json` (before or after the subcommand) for machine-readable output:

```bash
portly --json check 8000
# {"port": 8000, "available": true}
```

Exit codes: `0` success, `1` negative result or failure (port in use, timeout,
nothing to report), `2` usage error, `130` interrupted with Ctrl-C.

## API Reference

| Function | Description |
| --- | --- |
| `is_available(port: int) -> bool` | `True` if the port is free on localhost |
| `find_free(preferred: int \| None = None) -> int` | Returns `preferred` if free, otherwise any free port |
| `wait_until_free(port: int, timeout: int = 30) -> bool` | `True` when the port frees up, `False` on timeout |
| `get_info(port: int) -> PortInfo \| None` | `{"pid", "name", "cmd"}` for the listener, `None` if free |
| `kill(port: int, force: bool = False) -> bool` | Terminates the process(es) using the port |
| `scan(ports: list[int]) -> dict[int, PortInfo \| None]` | Process info per port |

`PortInfo` is a `TypedDict`: `{"pid": int, "name": str, "cmd": str}`.

### Platform notes

- **`get_info`** — `cmd` is the full command line on Linux, the executable
  path on macOS, and the executable name on Windows.
- **`kill`** — sends `SIGTERM` unless `force=True` (`SIGKILL`). On Windows the
  process is always terminated forcefully. Killing another user's process
  requires elevated privileges and raises `PermissionError` otherwise.
- **`find_free`** — the returned port can be taken between the check and your
  `bind()` (TOCTOU). If you need a race-free reservation, bind to port `0` and
  let the OS choose.
- **Visibility** — process info and kills only cover processes visible to your
  user; other users' listeners may report as "free"/unreachable without
  elevated privileges (same limitation as `lsof`).

## Why portly?

- **Cross-platform** — Linux, macOS, and Windows, with per-arch wheels.
- **Fast** — Rust core; no Python socket gymnastics, no subprocess spawning.
- **Correct** — native APIs (`/proc`, `libproc`, `GetExtendedTcpTable`), with
  graceful handling of zombies, permissions, and races.
- **Typed** — first-party type stubs checked against the compiled module.
- **Small** — six functions, one dependency-free story.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full setup. Quick start:

```bash
uv sync --group dev     # install dev dependencies (or use pip)
maturin develop         # build the extension in-place
pytest tests/           # run the tests
```

Quality gates: `cargo fmt`/`clippy`/`test`, `ruff check`/`format`, `mypy`,
and `mypy.stubtest`. All are enforced in CI.

## Examples

The [`examples/`](examples/) directory contains a FastAPI playground app that
exercises every function through a small web UI:

```bash
pip install fastapi uvicorn
uvicorn examples.main:app --reload --port 8712
```

## License

[MIT](LICENSE) © Patryk Bochenek