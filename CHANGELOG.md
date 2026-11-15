# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.4](https://github.com/PatrykBochenek/portly/compare/v0.2.3...v0.2.4) (2026-11-15)


### Bug Fixes

* validate port/count/timeout args in Python shim so bad values raise PortlyPortError ([#101](https://github.com/PatrykBochenek/portly/issues/101)) ([2cc5fa8](https://github.com/PatrykBochenek/portly/commit/2cc5fa80f384a3a6472163e47c090ecf5a05420f))

## [0.2.3](https://github.com/PatrykBochenek/portly/compare/v0.2.2...v0.2.3) (2026-11-14)


### Miscellaneous Chores

* rename build changelog section ([#64](https://github.com/PatrykBochenek/portly/issues/64)) ([4c10733](https://github.com/PatrykBochenek/portly/commit/4c10733302513aa94456fc658d81c2a6fc8be061))


### Dependencies

* **deps:** bump actions/configure-pages from 5.0.0 to 6.0.0 ([#36](https://github.com/PatrykBochenek/portly/issues/36)) ([4fcba76](https://github.com/PatrykBochenek/portly/commit/4fcba76b93aaf9dc6da99c1a97cb601a58c901ad))
* **deps:** bump actions/upload-artifact from 7.0.1 to 7.0.2 ([#93](https://github.com/PatrykBochenek/portly/issues/93)) ([4326579](https://github.com/PatrykBochenek/portly/commit/4326579897b2dea4b4cc51b55610166ceae270e8))
* **deps:** bump actions/upload-pages-artifact from 3.0.1 to 5.0.0 ([#35](https://github.com/PatrykBochenek/portly/issues/35)) ([a5b9784](https://github.com/PatrykBochenek/portly/commit/a5b9784e108c361498aa84b0e3f79f5dda93717a))
* **deps:** bump astral-sh/setup-uv from 10.1.0 to 10.2.0 ([#88](https://github.com/PatrykBochenek/portly/issues/88)) ([3fc2572](https://github.com/PatrykBochenek/portly/commit/3fc25728187a0922d857a6197a4618dfaaef9141))
* **deps:** bump codecov/codecov-action from 5.4.2 to 7.1.1 ([#86](https://github.com/PatrykBochenek/portly/issues/86)) ([52a13ad](https://github.com/PatrykBochenek/portly/commit/52a13ad28273f1b01d1a4d69bdfa5143b36eeec9))
* **deps:** bump libc from 0.2.189 to 0.2.191 ([#97](https://github.com/PatrykBochenek/portly/issues/97)) ([b134dab](https://github.com/PatrykBochenek/portly/commit/b134dabe9b23855e7375b6fcd14659cb30c9757c))
* **deps:** bump libproc from 0.14.11 to 0.15.0 ([#100](https://github.com/PatrykBochenek/portly/issues/100)) ([bf077af](https://github.com/PatrykBochenek/portly/commit/bf077aff47e33d9f35ae14abb02d9c5caa1e15f6))
* **deps:** bump pyo3 from 0.29.2 to 0.30.1 ([#95](https://github.com/PatrykBochenek/portly/issues/95)) ([613129c](https://github.com/PatrykBochenek/portly/commit/613129c2eec8608129991ec924c73222582e3401))
* **deps:** update fastapi requirement from &gt;=0.115 to &gt;=0.162.0 ([#99](https://github.com/PatrykBochenek/portly/issues/99)) ([7e09870](https://github.com/PatrykBochenek/portly/commit/7e09870997d6cb22fc7a77f4f21a2bad45cf8db4))
* **deps:** update uvicorn requirement from &gt;=0.52.4 to &gt;=0.54.0 ([#90](https://github.com/PatrykBochenek/portly/issues/90)) ([d2f3102](https://github.com/PatrykBochenek/portly/commit/d2f3102df37d2b24432c524244d1ec1aa0c19cb3))


### Continuous Integration

* remove temp `last-release-sha` pin ([#84](https://github.com/PatrykBochenek/portly/issues/84)) ([eb68953](https://github.com/PatrykBochenek/portly/commit/eb6895368c2f2450399f0b7f991fd4943add2978))

## [0.2.2](https://github.com/PatrykBochenek/portly/compare/v0.2.1...v0.2.2) (2026-09-17)


### Bug Fixes

* **kill:** refuse to terminate PID 0/1 ([#72](https://github.com/PatrykBochenek/portly/issues/72)) ([1953f8c](https://github.com/PatrykBochenek/portly/commit/1953f8c1f33d4a6cc7da1904dd78766dc952f5fb))

## [0.2.1](https://github.com/PatrykBochenek/portly/compare/v0.2.0...v0.2.1) (2026-09-15)


### Bug Fixes

* **bindings:** clamp wait_for_server attempt timeout and interval floor ([#69](https://github.com/PatrykBochenek/portly/issues/69)) ([a571926](https://github.com/PatrykBochenek/portly/commit/a571926fdace1843a957cb9d59ce9befb79177f7))
* handle CLI broken pipes without closing stderr ([#68](https://github.com/PatrykBochenek/portly/issues/68)) ([bdc84f3](https://github.com/PatrykBochenek/portly/commit/bdc84f3349928070dea329b3296c869e98d1cdbe))
* **kill:** guard against terminating the calling process (fixes [#49](https://github.com/PatrykBochenek/portly/issues/49)) ([#70](https://github.com/PatrykBochenek/portly/issues/70)) ([b9ca717](https://github.com/PatrykBochenek/portly/commit/b9ca7170592cc599f873229f42717b19da96ee13))
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
