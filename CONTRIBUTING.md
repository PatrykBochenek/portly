# Contributing to portly

Thanks for your interest in contributing! portly is a hybrid Python +
Rust package: a thin PyO3 extension over a pure-Rust core. Contributions of
all kinds are welcome — bug reports, docs, tests, and code.

## Development setup

Requirements: Python 3.10+, a Rust toolchain (rustc 1.85+), and
[uv](https://docs.astral.sh/uv/) (or pip).

```bash
# Clone the repo, then install dev dependencies.
uv sync --group dev

# Build and install the extension into the current environment.
maturin develop

# Run the tests.
pytest tests/
```

When you change Rust code you need to re-run `maturin develop` for the
Python tests to pick it up.

## Quality gates

All of the following must pass before merging. The CI runs the same checks.

```bash
# Rust
cargo fmt -- --check
cargo clippy --all-targets -- -D warnings
cargo test

# Python
ruff check python/ tests/ examples/
ruff format --check python/ tests/ examples/
mypy python/portly tests

# Stubs must match the compiled extension.
maturin develop
python -m mypy.stubtest portly._lib --allowlist tests/stubtest-allowlist.txt
```

There is also a pre-commit config; install it with
`pre-commit install` if you use pre-commit.

## Project layout

- `src/lib.rs` — the Rust extension. Platform-specific process lookup lives
  in `mod platform` (Linux: `procfs`, macOS: `libproc`, Windows:
  `windows-sys`). There are **no subprocess calls** — do not add `lsof`,
  `netstat`, `wmic`, or friends.
- `python/portly/` — the Python package: a thin re-export shim
  (`__init__.py`), the type stubs (`_lib.pyi`), and `py.typed`.
- `tests/` — pytest suite (run against the installed module) plus the
  stubtest allowlist.
- `examples/` — the FastAPI playground demo.

## Versioning and releases

portly follows [SemVer](https://semver.org/). The version is single-sourced in
`Cargo.toml`; `pyproject.toml` uses `dynamic = ["version"]`.

Releases are driven by [release-please](https://github.com/googleapis/release-please),
which parses conventional commits and maintains release PRs:

1. Merge conventional commits to `main` (`feat:` → minor, `fix:` → patch,
   `feat!:`/`fix!:`/`BREAKING CHANGE` → major; until v1.0, breaking changes
   bump minor only (`bump-minor-pre-major`)).
2. release-please opens a `chore(main): release vX.Y.Z` PR that bumps
   `Cargo.toml`/`Cargo.lock` and rewrites `CHANGELOG.md`.
3. Merge the release PR. release-please creates the `vX.Y.Z` tag and GitHub
   Release, then dispatches the `release.yml` workflow, which builds wheels for
   all platforms (manylinux/musllinux/Windows/macOS + sdist) and publishes to
   PyPI via Trusted Publishing with PEP 740 attestations.

Notes:

- The first release PR proposes `v0.1.0` (the rust release type's initial
  version) and includes the entire history.
- release-please uses `GITHUB_TOKEN`, so the repository setting **"Allow
  GitHub Actions to create and approve pull requests"** (Settings → Actions →
  General → Workflow permissions) must be enabled for CI to run on release PRs.
- The tag/dispatch is gated on the `release_created` output, so the release
  workflow only runs when release-please actually cut a release.

## Questions?

Open a discussion in the GitHub repo, or ask in your PR/issue.