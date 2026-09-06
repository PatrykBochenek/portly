# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1](https://github.com/PatrykBochenek/portly/compare/v0.2.0...v0.2.1) (2026-09-06)


### Bug Fixes

* **kill:** target TCP LISTEN sockets only, stop collateral UDP kills ([#71](https://github.com/PatrykBochenek/portly/issues/71)) ([a8470c8](https://github.com/PatrykBochenek/portly/commit/a8470c838407c8f208e02c4b33f8c0d0fdcf5152))
* **macos:** grow fd buffer and retry on listpidinfo race ([#74](https://github.com/PatrykBochenek/portly/issues/74)) ([c97b73e](https://github.com/PatrykBochenek/portly/commit/c97b73ec037ed4f8b52c0dd3d8c4eab45eb11d2a))
* reject lo=0 in find_free_in_range with ValueError ([#65](https://github.com/PatrykBochenek/portly/issues/65)) ([45d44da](https://github.com/PatrykBochenek/portly/commit/45d44da01282abe41e81740ad7a2fcbc7ca27e09))
* **windows:** propagate snapshot failure instead of silent kill success ([#73](https://github.com/PatrykBochenek/portly/issues/73)) ([4bf0c10](https://github.com/PatrykBochenek/portly/commit/4bf0c10610fa15d27ee81055312589490df34163))

## [0.2.0](https://github.com/PatrykBochenek/portly/compare/v0.1.0...v0.2.0) (2026-08-26)


### Features

* add portly CLI with check, find, scan, info, kill, and wait commands ([#39](https://github.com/PatrykBochenek/portly/issues/39)) ([8c278db](https://github.com/PatrykBochenek/portly/commit/8c278db6a06a82791c550fb16be3eeaea907684f))
* wait_for_server, find_free_in_range, exception hierarchy, probe tests, coverage ([#27](https://github.com/PatrykBochenek/portly/issues/27)) ([2352d38](https://github.com/PatrykBochenek/portly/commit/2352d38c3242e8d4460726c0833a268efdad621b))


### Bug Fixes

* make polling timeouts overflow-safe ([#30](https://github.com/PatrykBochenek/portly/issues/30)) ([706359b](https://github.com/PatrykBochenek/portly/commit/706359b5467349da36f274639a19dfa7e989699e))

## 0.1.0 (2026-08-16)


### Features

* rename python package and add typed stubs ([cfbcd68](https://github.com/PatrykBochenek/portly/commit/cfbcd68b18a2b7751837ed2d226caafb68cb2cda))


### Bug Fixes

* clippy flatten lint and Windows wheel install glob ([66c90dc](https://github.com/PatrykBochenek/portly/commit/66c90dce62e7259d935026cc26d4f9f1c1eb36a6))
* clippy manual-flatten on the Linux socket table loops ([061c010](https://github.com/PatrykBochenek/portly/commit/061c010ca90f53c6d3efc8e21c8a40709ab3678f))
* compile on Linux and Windows ([e300527](https://github.com/PatrykBochenek/portly/commit/e300527d5172146b0561a4bd47c127ee28c37d92))

## [Unreleased]

## [0.1.0] - 2026-08-16

### Added

- Initial release of **portly**: a cross-platform, Rust-powered library
  for checking, finding, scanning, waiting on, and freeing TCP/UDP ports.
- API: `is_available`, `find_free`, `wait_until_free`, `get_info`, `kill`,
  `scan`, `__version__`.
- Native (subprocess-free) process lookup on all platforms:
  - Linux: `/proc/net/{tcp,tcp6,udp,udp6}` + `/proc/<pid>/fd` via `procfs`.
  - macOS: `libproc` (`proc_pidinfo`).
  - Windows: `GetExtended{Tcp,Udp}Table` + ToolHelp32 via `windows-sys`
    (no dependency on the deprecated `wmic`).
- Type stubs (`_lib.pyi`) validated by `mypy.stubtest`; `py.typed` marker.
- CI: lint/typecheck gates, cross-platform test matrix (incl. free-threaded
  3.14t), wheel + sdist install tests, and a release workflow using PyPI
  Trusted Publishing with PEP 740 attestations.

[Unreleased]: https://github.com/PatrykBochenek/portly/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/PatrykBochenek/portly/releases/tag/v0.1.0
